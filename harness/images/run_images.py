#!/usr/bin/env python3
"""Run the fixed image generation and editing matrix through public AI-Lab APIs."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import struct
import sys
import time

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from harness.shared.lab import MANAGER_HELP, api, manager_url, multipart, read_error, unload_running, write_json

# A PNG starts with this signature; its width and height follow at bytes 16-24.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_SIZE_END = 24
FINISHED = {"succeeded", "failed", "cancelled"}


PROFILES = (
    ("sd15-smoke", "image-smoke", "generation"),
    ("qwen-image-benchmark", "image-qwen", "generation"),
    ("flux2-benchmark", "image-flux2", "generation"),
    ("flux2-dev-bf16-benchmark", "macos-image-flux2-dev-bf16", "generation"),
    ("flux2-dev-q8-benchmark", "image-flux2-dev-q8-0", "generation"),
    ("flux2-klein-4b-benchmark", "image-flux2-klein-4b", "generation"),
    ("qwen-edit-benchmark", "macos-image-qwen-edit", "edit"),
)


def load(base: str, instance: str) -> dict:
    """Load one instance; ok, wall time and the manager's whole answer."""
    started = time.perf_counter()
    try:
        value = api(base, f"/api/instances/{instance}/load", "POST", timeout=600)
        operation = value.get("operation") or value
        return {"ok": bool(operation.get("ok", value.get("ok", True))),
                "wall_s": round(time.perf_counter() - started, 3),
                "manager": value}
    except Exception as error:
        return {"ok": False, "wall_s": round(time.perf_counter() - started, 3),
                "error": read_error(error)}


def wait_job(base: str, job_id: str, timeout_s: int = 7200) -> dict:
    """Poll an image job until it finishes; its last state."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        job = api(base, f"/api/image-jobs/{job_id}")
        if job.get("status") in FINISHED:
            return job
        time.sleep(2)
    raise TimeoutError(f"image job {job_id} exceeded {timeout_s}s")


def png_facts(payload: bytes) -> dict:
    """Size, checksum, whether it is a PNG, and its width and height if so."""
    facts: dict = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                   "png": payload.startswith(PNG_SIGNATURE)}
    if facts["png"] and len(payload) >= PNG_SIZE_END:
        facts["width"], facts["height"] = struct.unpack(">II", payload[16:PNG_SIZE_END])
    return facts


def submit(manager: str, out: pathlib.Path, profile: str, task: str, case: dict) -> dict:
    """Start one generation or edit as a job; the job as the manager answered."""
    if task == "generation":
        return api(manager, "/v1/images/generations", "POST",
                   body={"profile": profile, "prompt": case["prompt"], "async": True})
    source = out / "library" / case["source"]
    return multipart(manager + "/v1/images/edits",
                     {"profile": profile, "prompt": case["prompt"], "async": "true"},
                     ("image", source.name, source.read_bytes()), timeout=120)


def run_case(manager: str, out: pathlib.Path, profile: str, task: str, case: dict) -> dict:
    """One case: the job, its result saved under the library, and its facts."""
    record = {"case": case["id"], "prompt": case["prompt"], "rubric": case["rubric"], "ok": False}
    if task != "generation":
        record["source"] = str(pathlib.Path("library") / case["source"])
    try:
        job = submit(manager, out, profile, task, case)
        record["job_id"] = job["id"]
        result = wait_job(manager, job["id"])
        record.update({"status": result.get("status"), "duration_ms": result.get("duration_ms"),
                       "effective_settings": result.get("effective_settings", {})})
        if result.get("status") != "succeeded":
            record["error"] = result.get("error", "job failed")
            return record
        image = base64.b64decode(result["result"]["data"][0]["b64_json"])
        destination = out / "library" / profile / f"{case['id']}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(image)
        record.update({"ok": True, "artifact": str(destination.relative_to(out)),
                       "deterministic": png_facts(image),
                       "semantic_review": {"status": "pending", "scores": {}, "notes": ""}})
    except Exception as error:
        record.update({"status": "failed", "error": read_error(error)})
    return record


class ProfileRun:
    """The run's manager, output folder and summary, saved after every step."""

    def __init__(self, manager: str, out: pathlib.Path, summary_path: pathlib.Path,
                 summary: dict) -> None:
        self.manager = manager
        self.out = out
        self.summary_path = summary_path
        self.summary = summary

    def save(self) -> None:
        """The summary, on disk."""
        write_json(self.summary_path, self.summary)

    def profile(self, profile: str, instance: str, task: str, cases: list[dict]) -> None:
        """Load one profile's model, run the cases not done yet, unload it."""
        entry = self.summary["profiles"].setdefault(profile, {
            "instance": instance, "task": task, "cases": []})
        entry["preload_unloads"] = unload_running(self.manager)
        entry["load"] = load(self.manager, instance)
        self.save()
        if not entry["load"]["ok"]:
            print(f"{profile}: load FAILED", flush=True)
            return
        done = {item["case"] for item in entry["cases"]}
        for case in cases:
            if case["id"] in done:
                continue
            record = run_case(self.manager, self.out, profile, task, case)
            entry["cases"].append(record)
            self.save()
            print(f"{profile} {case['id']}: {'ok' if record['ok'] else 'FAILED'}", flush=True)
        try:
            entry["unload"] = api(self.manager, f"/api/instances/{instance}/unload", "POST", 300)
        except Exception as error:
            entry["unload"] = {"ok": False, "error": read_error(error)}
        self.save()


def main() -> int:
    """Run every profile (or those in `--profiles`), keeping cases already done."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", help=MANAGER_HELP)
    parser.add_argument("--cases", default=str(pathlib.Path(__file__).with_name("cases.json")))
    parser.add_argument("--out", required=True)
    parser.add_argument("--profiles", help="comma-separated profile ids")
    args = parser.parse_args()
    manager = manager_url(args.manager)
    matrix = json.loads(pathlib.Path(args.cases).read_text())
    out = pathlib.Path(args.out)
    summary_path = out / "summary.json"
    summary: dict = json.loads(summary_path.read_text()) if summary_path.exists() else {
        "schema_version": 1, "manager": "AI-Lab manager (address not recorded)", "profiles": {}}
    wanted = set(args.profiles.split(",")) if args.profiles else None
    run = ProfileRun(manager, out, summary_path, summary)
    for profile, instance, task in PROFILES:
        if not wanted or profile in wanted:
            run.profile(profile, instance, task, matrix["generation" if task == "generation"
                                                       else "edits"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
