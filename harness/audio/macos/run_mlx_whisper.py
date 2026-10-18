#!/usr/bin/env python3
"""Run the shared Romanian FLEURS fixture locally with MLX Whisper on macOS."""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import resource
import subprocess
import sys
import time

import mlx_whisper

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from harness.shared.textmetrics import ErrorTotals

FIXTURE = "google/fleurs:ro_ro:test:evenly-spaced-100"


def hardware() -> dict:
    """The Mac, the runtime and its version, as recorded with every result."""
    chip = subprocess.run(
        ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
        text=True, check=False).stdout.strip()
    memory = subprocess.run(
        ["sysctl", "-n", "hw.memsize"], capture_output=True,
        text=True, check=False).stdout.strip()
    return {
        "os": platform.mac_ver()[0],
        "architecture": platform.machine(),
        "chip": chip,
        "memory_bytes": int(memory) if memory.isdigit() else None,
        "python": platform.python_version(),
        "runtime": "mlx-whisper",
        "runtime_version": getattr(mlx_whisper, "__version__", None),
    }


def peak_rss_bytes() -> int:
    """The most memory this process has held so far."""
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def transcribe(path: pathlib.Path, model: str) -> str:
    """One recording's text, in Romanian."""
    result = mlx_whisper.transcribe(
        str(path), path_or_hf_repo=model, language="ro", verbose=False)
    return str(result.get("text") or "")


class Run:
    """One pass over the fixture: what is recorded, and where it is written."""

    def __init__(self, data: pathlib.Path, out: pathlib.Path, model: str) -> None:
        self.data = data
        self.out = out
        self.model = model
        out.mkdir(parents=True, exist_ok=True)
        self.manifest = json.loads((data / "MANIFEST.json").read_text(encoding="utf-8"))
        self.totals = ErrorTotals()
        self.standardized: list[dict] = []
        self.raw: dict = {
            "schema_version": 1, "platform": "macOS", "hardware_runtime": hardware(),
            "profile": "whisper-large-v3-turbo-mlx-fp16", "model": model,
            "fixture": {
                "dataset": "google/fleurs", "config": "ro_ro", "split": "test",
                "selection": self.manifest["selection"],
                "cases": len(self.manifest["items"]),
                "audio_duration_s": self.manifest["audio_duration_s"],
            },
            "warmup": None, "cases": [], "incidents": [],
        }

    def write(self, *, summary: bool = False) -> None:
        """Everything recorded so far, on disk."""
        self._dump("raw.json", self.raw)
        self._dump("incidents.json", self.raw["incidents"])
        if summary:
            self._dump("summary.json", self.raw["summary"])

    def _dump(self, name: str, value) -> None:
        (self.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def warm_up(self) -> bool:
        """One transcription not scored; a failure is an incident and ends the run."""
        started = time.perf_counter()
        warmup: dict = {"ok": True, "excluded_from_scoring": True}
        try:
            transcribe(self.data / self.manifest["items"][0]["path"], self.model)
        except Exception as error:
            warmup.update(ok=False, error=f"{type(error).__name__}: {error}")
            self.raw["incidents"].append({
                "stage": "warmup", "incident_category": "configuration_or_infrastructure",
                "reached_model_execution": False, "note": warmup["error"]})
        warmup["latency_s"] = round(time.perf_counter() - started, 6)
        self.raw["warmup"] = warmup
        return bool(warmup["ok"])

    def case(self, item: dict) -> dict:
        """One recording: transcribed, scored, with the memory held at the end."""
        started = time.perf_counter()
        record = {"ordinal": item["ordinal"], "id": item["id"],
                  "source_row": item["source_row"], "duration_s": item["duration_s"],
                  "reached_model_execution": True}
        try:
            hypothesis = transcribe(self.data / item["path"], self.model)
            latency = time.perf_counter() - started
            words_wrong, words, chars_wrong, chars = self.totals.add(item["reference"], hypothesis)
            record.update({"outcome": "success", "latency_s": round(latency, 6),
                           "word_errors": words_wrong, "reference_words": words,
                           "char_errors": chars_wrong, "reference_chars": chars})
        except Exception as error:
            record.update({"outcome": "model_failure",
                           "latency_s": round(time.perf_counter() - started, 6),
                           "error": f"{type(error).__name__}: {error}"})
        record["peak_process_rss_bytes"] = peak_rss_bytes()
        return record

    def standard_row(self, item: dict, record: dict) -> dict:
        """The case in the shape shared by every platform's results."""
        return {
            "schema_version": 1, "platform": "macOS",
            "hardware_runtime": self.raw["hardware_runtime"], "profile": self.raw["profile"],
            "model": self.model, "fixture": FIXTURE,
            "case": {"ordinal": item["ordinal"], "id": item["id"],
                     "source_row": item["source_row"], "duration_s": item["duration_s"]},
            "reached_model_execution": record["reached_model_execution"],
            "outcome": record["outcome"], "latency_s": record["latency_s"],
            "resources": {"peak_process_rss_bytes": record["peak_process_rss_bytes"]},
            "incident_category": None, "notes": record.get("error"),
        }

    def all_cases(self) -> None:
        """Every recording, written as it goes."""
        items = self.manifest["items"]
        for position, item in enumerate(items, 1):
            record = self.case(item)
            self.raw["cases"].append(record)
            self.standardized.append(self.standard_row(item, record))
            self.write()
            (self.out / "standardized-cases.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in self.standardized),
                encoding="utf-8")
            print(f"{position}/{len(items)} {record['outcome']}", flush=True)

    def summarize(self) -> int:
        """The run's figures; the number of failed cases."""
        cases = self.raw["cases"]
        failed = sum(case["outcome"] == "model_failure" for case in cases)
        inference_s = sum(case["latency_s"] for case in cases if case["outcome"] == "success")
        audio_s = self.manifest["audio_duration_s"]
        self.raw["summary"] = {
            "cases": len(cases), "reached_model_execution": len(cases),
            "successful": sum(case["outcome"] == "success" for case in cases),
            "model_failures": failed, "incidents": len(self.raw["incidents"]),
            "inference_s": round(inference_s, 6),
            "real_time_factor": round(inference_s / audio_s, 6) if inference_s else None,
            "audio_seconds_per_second": round(audio_s / inference_s, 3) if inference_s else None,
            **self.totals.rates(),
        }
        return failed


def main() -> int:
    """Warm up, transcribe every case, summarise; 2 if the warm-up failed, 1 if a case did."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    args = parser.parse_args()
    run = Run(pathlib.Path(args.data), pathlib.Path(args.out), args.model)
    if not run.warm_up():
        run.write()
        return 2
    run.all_cases()
    failed = run.summarize()
    run.write(summary=True)
    print(json.dumps(run.raw["summary"], indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
