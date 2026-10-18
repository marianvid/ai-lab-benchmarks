#!/usr/bin/env python3
"""Run the Romanian ASR study through AI-Lab and preserve every outcome."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from harness.shared.lab import MANAGER_HELP, manager_url, multipart, read_error, timed, unload_running
from harness.shared.textmetrics import ErrorTotals

MODELS = [
    ("whisper-large-v3", "Whisper large-v3", "vLLM", "Safetensors"),
    ("whisper-large-v3-turbo", "Whisper large-v3-turbo", "vLLM", "Safetensors"),
    ("qwen3-asr-06b", "Qwen3-ASR-0.6B", "vLLM", "Safetensors"),
    ("qwen3-asr-17b", "Qwen3-ASR-1.7B", "vLLM", "Safetensors"),
    ("parakeet-tdt-06b-v3", "Parakeet TDT 0.6B v3", "NeMo", ".nemo"),
    ("canary-1b-v2", "Canary 1B v2", "NeMo", ".nemo"),
    ("nemotron-35-asr-streaming-06b", "Nemotron 3.5 ASR Streaming 0.6B", "NeMo", ".nemo"),
]
TRANSCRIPTIONS = "/v1/audio/transcriptions"
NOTHING_SCORED = {"real_time_factor": None, "audio_seconds_per_second": None,
                  "wer": None, "cer": None, "wer_without_diacritics": None,
                  "cer_without_diacritics": None}


class Study:
    """One run of the study: where the data is, where the results go, the manager."""

    def __init__(self, manager: str, data: pathlib.Path, out: pathlib.Path) -> None:
        self.manager = manager
        self.data = data
        self.manifest = json.loads((data / "MANIFEST.json").read_text(encoding="utf-8"))
        self.details_dir = out / "details"
        self.details_dir.mkdir(parents=True, exist_ok=True)
        self.summary_path = out / "summary.json"
        self.summary = (json.loads(self.summary_path.read_text())
                        if self.summary_path.exists() else {})

    def transcribe(self, instance: str, audio: pathlib.Path) -> dict:
        """One recording through the gateway, in Romanian."""
        return multipart(self.manager + TRANSCRIPTIONS, {"model": instance, "language": "ro"},
                         ("file", audio.name, audio.read_bytes()))

    def save(self, instance: str, entry: dict) -> None:
        """Record one model's entry in the summary, at once."""
        self.summary[instance] = entry
        self.summary_path.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2) + "\n")

    def details(self, instance: str, items: list[dict], status: str | None = None) -> None:
        """Every request of one model, written as the run goes."""
        record: dict = {"schema_version": 1, "instance": instance}
        if status:
            record["status"] = status
        record["items"] = items
        (self.details_dir / f"{instance}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    def run_model(self, instance: str, label: str, engine: str, weight_format: str) -> None:
        """Load one model, warm it, transcribe every recording, unload; record it all."""
        print(f"--- {instance}: {label} ---", flush=True)
        entry = {
            "instance": instance, "model": label, "engine": engine,
            "format": weight_format, "dataset": "google/fleurs ro_ro test",
            "selected_rows": len(self.manifest["items"]),
            "audio_duration_s": self.manifest["audio_duration_s"],
            "preload_unloads": unload_running(self.manager),
        }
        entry["load"] = timed(self.manager, instance, "load")
        if not entry["load"]["ok"]:
            self.save(instance, entry)
            return
        entry["warmup"] = self.warm_up(instance)
        if not entry["warmup"]["ok"]:
            self.warmup_failed(instance, entry)
            return
        results, inference_s, totals = self.transcribe_all(instance)
        entry.update(scores(results, inference_s, totals, self.manifest["audio_duration_s"]))
        entry["unload"] = timed(self.manager, instance, "unload")
        self.save(instance, entry)
        print(f"  WER={entry['wer']} RTF={entry['real_time_factor']}", flush=True)

    def warm_up(self, instance: str) -> dict:
        """Exercise decoder setup and kernels once, exactly as the text study does.

        The warm-up is recorded but never scored or timed into RTF.
        """
        audio = self.data / self.manifest["items"][0]["path"]
        started = time.perf_counter()
        try:
            self.transcribe(instance, audio)
            return {"ok": True, "wall_s": round(time.perf_counter() - started, 6)}
        except Exception as error:
            return {"ok": False, "wall_s": round(time.perf_counter() - started, 6),
                    "error": read_error(error)}

    def warmup_failed(self, instance: str, entry: dict) -> None:
        """A model that cannot answer once is recorded as such, and unloaded."""
        entry.update({"status": "warmup_failed", "requests": 0, "successful": 0,
                      "failed": 0, "inference_s": 0.0, **NOTHING_SCORED})
        self.details(instance, [], "warmup_failed")
        unloaded = timed(self.manager, instance, "unload")
        if not unloaded["ok"]:
            entry["unload"] = {"ok": False, "error": unloaded.get("error")}
        self.save(instance, entry)
        print(f"  warm-up FAILED: {entry['warmup']['error']}", flush=True)

    def transcribe_all(self, instance: str) -> tuple[list[dict], float, ErrorTotals]:
        """Every recording once: per-item records, total inference time, error totals."""
        items = self.manifest["items"]
        results: list[dict] = []
        inference_s = 0.0
        totals = ErrorTotals()
        for position, item in enumerate(items):
            record, elapsed = self.transcribe_item(instance, item, totals)
            inference_s += elapsed
            results.append(record)
            self.details(instance, results)
            print(f"  {position + 1}/{len(items)} {'ok' if record['ok'] else 'FAILED'}",
                  flush=True)
        return results, inference_s, totals

    def transcribe_item(self, instance: str, item: dict,
                        totals: ErrorTotals) -> tuple[dict, float]:
        """One recording: its record, and the inference time it counts for (0 if it failed)."""
        audio = self.data / item["path"]
        started = time.perf_counter()
        record = {"ordinal": item["ordinal"], "id": item["id"],
                  "source_row": item["source_row"], "duration_s": item["duration_s"]}
        try:
            response = self.transcribe(instance, audio)
        except Exception as error:
            record.update({"ok": False, "error": read_error(error),
                           "inference_s": round(time.perf_counter() - started, 6)})
            return record, 0.0
        elapsed = time.perf_counter() - started
        counted = totals.add(item["reference"], str(response.get("text") or ""))
        record.update({"ok": True, "inference_s": round(elapsed, 6),
                       "word_errors": counted[0], "reference_words": counted[1],
                       "char_errors": counted[2], "reference_chars": counted[3]})
        return record, elapsed


def ratio(part: float, whole: float, digits: int) -> float | None:
    """part / whole rounded, or None when there is nothing to divide by."""
    return round(part / whole, digits) if whole else None


def scores(results: list[dict], inference_s: float, totals: ErrorTotals,
           audio_s: float) -> dict:
    """One model's figures: requests, speed and error rates."""
    successful = sum(bool(item["ok"]) for item in results)
    return {
        "requests": len(results), "successful": successful,
        "failed": len(results) - successful,
        "inference_s": round(inference_s, 3),
        "real_time_factor": round(inference_s / audio_s, 4),
        "audio_seconds_per_second": ratio(audio_s, inference_s, 3),
        **totals.rates(),
        "error_totals": totals.counts,
    }


def main() -> int:
    """Run every model (or those in `--only`) and keep each outcome."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", help=MANAGER_HELP)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", help="comma-separated instance ids")
    args = parser.parse_args()
    study = Study(manager_url(args.manager), pathlib.Path(args.data), pathlib.Path(args.out))
    wanted = set(args.only.split(",")) if args.only else None
    for model in MODELS:
        if not wanted or model[0] in wanted:
            study.run_model(*model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
