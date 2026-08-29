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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from run_asr import error_counts  # noqa: E402


def hardware() -> dict:
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
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def transcribe(path: pathlib.Path, model: str) -> str:
    result = mlx_whisper.transcribe(
        str(path), path_or_hf_repo=model, language="ro", verbose=False)
    return str(result.get("text") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    args = parser.parse_args()

    data = pathlib.Path(args.data)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((data / "MANIFEST.json").read_text(encoding="utf-8"))
    raw_path = out / "raw.json"
    standardized_path = out / "standardized-cases.jsonl"
    incidents_path = out / "incidents.json"
    raw = {
        "schema_version": 1,
        "platform": "macOS",
        "hardware_runtime": hardware(),
        "profile": "whisper-large-v3-turbo-mlx-fp16",
        "model": args.model,
        "fixture": {
            "dataset": "google/fleurs",
            "config": "ro_ro",
            "split": "test",
            "selection": manifest["selection"],
            "cases": len(manifest["items"]),
            "audio_duration_s": manifest["audio_duration_s"],
        },
        "warmup": None,
        "cases": [],
        "incidents": [],
    }

    warmup = data / manifest["items"][0]["path"]
    started = time.perf_counter()
    try:
        transcribe(warmup, args.model)
        raw["warmup"] = {
            "ok": True,
            "latency_s": round(time.perf_counter() - started, 6),
            "excluded_from_scoring": True,
        }
    except Exception as error:
        raw["warmup"] = {
            "ok": False,
            "latency_s": round(time.perf_counter() - started, 6),
            "excluded_from_scoring": True,
            "error": f"{type(error).__name__}: {error}",
        }
        raw["incidents"].append({
            "stage": "warmup",
            "incident_category": "configuration_or_infrastructure",
            "reached_model_execution": False,
            "note": raw["warmup"]["error"],
        })
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
        incidents_path.write_text(json.dumps(raw["incidents"], ensure_ascii=False, indent=2) + "\n")
        return 2

    totals = {
        "word_errors": 0, "words": 0, "char_errors": 0, "chars": 0,
        "ascii_word_errors": 0, "ascii_words": 0,
        "ascii_char_errors": 0, "ascii_chars": 0,
    }
    standardized = []
    for position, item in enumerate(manifest["items"], 1):
        wav = data / item["path"]
        started = time.perf_counter()
        record = {
            "ordinal": item["ordinal"],
            "id": item["id"],
            "source_row": item["source_row"],
            "duration_s": item["duration_s"],
            "reached_model_execution": True,
        }
        try:
            hypothesis = transcribe(wav, args.model)
            latency = time.perf_counter() - started
            we, words, ce, chars = error_counts(item["reference"], hypothesis)
            awe, awords, ace, achars = error_counts(item["reference"], hypothesis, True)
            for key, value in (
                ("word_errors", we), ("words", words),
                ("char_errors", ce), ("chars", chars),
                ("ascii_word_errors", awe), ("ascii_words", awords),
                ("ascii_char_errors", ace), ("ascii_chars", achars),
            ):
                totals[key] += value
            record.update({
                "outcome": "success", "latency_s": round(latency, 6),
                "word_errors": we, "reference_words": words,
                "char_errors": ce, "reference_chars": chars,
                "peak_process_rss_bytes": peak_rss_bytes(),
            })
        except Exception as error:
            record.update({
                "outcome": "model_failure",
                "latency_s": round(time.perf_counter() - started, 6),
                "error": f"{type(error).__name__}: {error}",
                "peak_process_rss_bytes": peak_rss_bytes(),
            })
        raw["cases"].append(record)
        standardized.append({
            "schema_version": 1,
            "platform": "macOS",
            "hardware_runtime": raw["hardware_runtime"],
            "profile": raw["profile"],
            "model": args.model,
            "fixture": "google/fleurs:ro_ro:test:evenly-spaced-100",
            "case": {"ordinal": item["ordinal"], "id": item["id"],
                     "source_row": item["source_row"],
                     "duration_s": item["duration_s"]},
            "reached_model_execution": record["reached_model_execution"],
            "outcome": record["outcome"],
            "latency_s": record["latency_s"],
            "resources": {"peak_process_rss_bytes": record["peak_process_rss_bytes"]},
            "incident_category": None,
            "notes": record.get("error"),
        })
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
        standardized_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in standardized),
            encoding="utf-8")
        print(f"{position}/{len(manifest['items'])} {record['outcome']}", flush=True)

    successful = sum(case["outcome"] == "success" for case in raw["cases"])
    failed = sum(case["outcome"] == "model_failure" for case in raw["cases"])
    inference_s = sum(case["latency_s"] for case in raw["cases"]
                      if case["outcome"] == "success")
    raw["summary"] = {
        "cases": len(raw["cases"]),
        "reached_model_execution": len(raw["cases"]),
        "successful": successful,
        "model_failures": failed,
        "incidents": len(raw["incidents"]),
        "inference_s": round(inference_s, 6),
        "real_time_factor": round(inference_s / manifest["audio_duration_s"], 6)
            if inference_s else None,
        "audio_seconds_per_second": round(manifest["audio_duration_s"] / inference_s, 3)
            if inference_s else None,
        "wer": round(totals["word_errors"] / totals["words"], 6)
            if totals["words"] else None,
        "cer": round(totals["char_errors"] / totals["chars"], 6)
            if totals["chars"] else None,
        "wer_without_diacritics": round(
            totals["ascii_word_errors"] / totals["ascii_words"], 6)
            if totals["ascii_words"] else None,
        "cer_without_diacritics": round(
            totals["ascii_char_errors"] / totals["ascii_chars"], 6)
            if totals["ascii_chars"] else None,
    }
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    incidents_path.write_text(json.dumps(raw["incidents"], ensure_ascii=False, indent=2) + "\n")
    (out / "summary.json").write_text(
        json.dumps(raw["summary"], ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(raw["summary"], indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
