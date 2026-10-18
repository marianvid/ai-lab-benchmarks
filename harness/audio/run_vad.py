#!/usr/bin/env python3
"""Measure Silero VAD transport and processing speed on Romanian FLEURS audio.

FLEURS has transcription but no speech-boundary annotations. This is therefore
a technical throughput and stability measurement, not a VAD quality score.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from harness.shared.lab import (MANAGER_HELP, manager_url, multipart, read_error, timed, unload_running,
                        unreachable)

INSTANCE = "silero-vad"


def segment_one(manager: str, data: pathlib.Path, item: dict) -> dict:
    """One recording: its speech segments and how long finding them took."""
    wav = data / item["path"]
    started = time.perf_counter()
    record = {"ordinal": item["ordinal"], "id": item["id"], "duration_s": item["duration_s"]}
    try:
        response = multipart(manager + "/v1/audio/speech-segments", {"model": INSTANCE},
                             ("file", wav.name, wav.read_bytes()))
    except Exception as error:
        record.update({"ok": False, "error": read_error(error)})
        return record
    elapsed = time.perf_counter() - started
    segments = response.get("segments") or []
    record.update({"ok": True, "inference_s": round(elapsed, 6), "segments": segments,
                   "detected_speech_s": round(sum(max(0, segment["end"] - segment["start"])
                                                  for segment in segments), 6)})
    return record


def summary(items: list[dict], duration_s: float) -> dict:
    """Requests, successes, and the speed over the successful ones."""
    total_s = sum(item.get("inference_s", 0.0) for item in items if item["ok"])
    return {
        "requests": len(items), "successful": sum(bool(item["ok"]) for item in items),
        "audio_duration_s": duration_s, "inference_s": round(total_s, 3),
        "real_time_factor": round(total_s / duration_s, 6),
        "audio_seconds_per_second": round(duration_s / total_s, 3) if total_s else None,
    }


def main() -> int:
    """Load Silero, segment every recording, unload; 1 if it would not load."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", help=MANAGER_HELP)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    manager = manager_url(args.manager)
    data = pathlib.Path(args.data)
    manifest = json.loads((data / "MANIFEST.json").read_text())
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def write() -> None:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    result: dict = {"instance": INSTANCE, "model": "Silero VAD 6.2.1",
                    "dataset": "google/fleurs ro_ro test",
                    "measurement": "technical throughput; no boundary ground truth",
                    "preload_unloads": unload_running(manager), "items": []}
    result["load"] = timed(manager, INSTANCE, "load")
    if unreachable(result["load"]):
        write()
        return 1
    for item in manifest["items"]:
        result["items"].append(segment_one(manager, data, item))
        write()
    result["summary"] = summary(result["items"], manifest["audio_duration_s"])
    unloaded = timed(manager, INSTANCE, "unload")
    if unreachable(unloaded):
        result["unload_error"] = unloaded["error"]
    write()
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
