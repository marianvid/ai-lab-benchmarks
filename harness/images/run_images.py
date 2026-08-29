#!/usr/bin/env python3
"""Run the fixed image generation and editing matrix through public AI-Lab APIs."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import struct
import time
import urllib.error
import urllib.request
import uuid


PROFILES = (
    ("sd15-smoke", "image-smoke", "generation"),
    ("qwen-image-benchmark", "image-qwen", "generation"),
    ("flux2-benchmark", "image-flux2", "generation"),
    ("flux2-dev-bf16-benchmark", "macos-image-flux2-dev-bf16", "generation"),
    ("flux2-dev-q8-benchmark", "image-flux2-dev-q8-0", "generation"),
    ("flux2-klein-4b-benchmark", "image-flux2-klein-4b", "generation"),
    ("qwen-edit-benchmark", "macos-image-qwen-edit", "edit"),
)


def request(base: str, path: str, method: str = "GET", body=None,
            timeout: int = 1800):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if data else {}
    call = urllib.request.Request(base + path, data=data, method=method,
                                  headers=headers)
    with urllib.request.urlopen(call, timeout=timeout) as response:
        return json.load(response)


def error_text(error: Exception) -> str:
    if isinstance(error, urllib.error.HTTPError):
        try:
            return error.read().decode("utf-8", "replace")
        except Exception:
            pass
    return f"{type(error).__name__}: {error}"


def unload_all(base: str) -> list[dict]:
    outcomes = []
    for item in request(base, "/api/instances"):
        if not item.get("running"):
            continue
        try:
            value = request(base, f"/api/instances/{item['id']}/unload", "POST", timeout=300)
            outcomes.append({"id": item["id"], "ok": bool(value.get("ok", True))})
        except Exception as error:
            outcomes.append({"id": item["id"], "ok": False,
                             "error": error_text(error)})
    return outcomes


def load(base: str, instance: str) -> dict:
    started = time.perf_counter()
    try:
        value = request(base, f"/api/instances/{instance}/load", "POST", timeout=600)
        operation = value.get("operation") or value
        return {"ok": bool(operation.get("ok", value.get("ok", True))),
                "wall_s": round(time.perf_counter() - started, 3),
                "manager": value}
    except Exception as error:
        return {"ok": False, "wall_s": round(time.perf_counter() - started, 3),
                "error": error_text(error)}


def multipart(url: str, fields: dict[str, str], image: pathlib.Path,
              timeout: int = 120) -> dict:
    boundary = "ai-lab-image-benchmark-" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks += [f"--{boundary}\r\n".encode(),
                   f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                   value.encode(), b"\r\n"]
    chunks += [f"--{boundary}\r\n".encode(),
               f'Content-Disposition: form-data; name="image"; filename="{image.name}"\r\n'.encode(),
               b"Content-Type: image/png\r\n\r\n", image.read_bytes(), b"\r\n",
               f"--{boundary}--\r\n".encode()]
    call = urllib.request.Request(url, data=b"".join(chunks), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(call, timeout=timeout) as response:
        return json.load(response)


def wait_job(base: str, job_id: str, timeout_s: int = 7200) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        job = request(base, f"/api/image-jobs/{job_id}")
        if job.get("status") in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(2)
    raise TimeoutError(f"image job {job_id} exceeded {timeout_s}s")


def png_facts(payload: bytes) -> dict:
    facts = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
             "png": payload.startswith(b"\x89PNG\r\n\x1a\n")}
    if facts["png"] and len(payload) >= 24:
        facts["width"], facts["height"] = struct.unpack(">II", payload[16:24])
    return facts


def save(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", default="http://192.168.50.222:8090")
    parser.add_argument("--cases", default=str(pathlib.Path(__file__).with_name("cases.json")))
    parser.add_argument("--out", required=True)
    parser.add_argument("--profiles", help="comma-separated profile ids")
    args = parser.parse_args()
    matrix = json.loads(pathlib.Path(args.cases).read_text())
    out = pathlib.Path(args.out)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {
        "schema_version": 1, "manager": args.manager, "profiles": {}}
    wanted = set(args.profiles.split(",")) if args.profiles else None

    for profile, instance, task in PROFILES:
        if wanted and profile not in wanted:
            continue
        cases = matrix["generation" if task == "generation" else "edits"]
        entry = summary["profiles"].setdefault(profile, {
            "instance": instance, "task": task, "cases": []})
        entry["preload_unloads"] = unload_all(args.manager)
        entry["load"] = load(args.manager, instance)
        save(summary_path, summary)
        if not entry["load"]["ok"]:
            print(f"{profile}: load FAILED", flush=True)
            continue
        done = {item["case"] for item in entry["cases"]}
        for case in cases:
            if case["id"] in done:
                continue
            record = {"case": case["id"], "prompt": case["prompt"],
                      "rubric": case["rubric"], "ok": False}
            try:
                if task == "generation":
                    job = request(args.manager, "/v1/images/generations", "POST",
                                  {"profile": profile, "prompt": case["prompt"],
                                   "async": True})
                else:
                    source = out / "library" / case["source"]
                    record["source"] = str(source.relative_to(out))
                    job = multipart(args.manager + "/v1/images/edits",
                        {"profile": profile, "prompt": case["prompt"], "async": "true"},
                        source)
                record["job_id"] = job["id"]
                result = wait_job(args.manager, job["id"])
                record.update({"status": result.get("status"),
                               "duration_ms": result.get("duration_ms"),
                               "effective_settings": result.get("effective_settings", {})})
                if result.get("status") != "succeeded":
                    record["error"] = result.get("error", "job failed")
                else:
                    image = base64.b64decode(result["result"]["data"][0]["b64_json"])
                    destination = out / "library" / profile / f"{case['id']}.png"
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(image)
                    record.update({"ok": True,
                                   "artifact": str(destination.relative_to(out)),
                                   "deterministic": png_facts(image),
                                   "semantic_review": {"status": "pending", "scores": {},
                                                       "notes": ""}})
            except Exception as error:
                record.update({"status": "failed", "error": error_text(error)})
            entry["cases"].append(record)
            save(summary_path, summary)
            print(f"{profile} {case['id']}: {'ok' if record['ok'] else 'FAILED'}", flush=True)
        try:
            entry["unload"] = request(args.manager,
                                      f"/api/instances/{instance}/unload", "POST", timeout=300)
        except Exception as error:
            entry["unload"] = {"ok": False, "error": error_text(error)}
        save(summary_path, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
