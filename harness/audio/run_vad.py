#!/usr/bin/env python3
"""Measure Silero VAD transport and processing speed on Romanian FLEURS audio.

FLEURS has transcription but no speech-boundary annotations. This is therefore
a technical throughput and stability measurement, not a VAD quality score.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

from run_asr import api, multipart, read_error, unload_running


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", default="http://192.168.50.222:8090")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = pathlib.Path(args.data)
    manifest = json.loads((data / "MANIFEST.json").read_text())
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {"instance": "silero-vad", "model": "Silero VAD 6.2.1",
              "dataset": "google/fleurs ro_ro test",
              "measurement": "technical throughput; no boundary ground truth",
              "preload_unloads": unload_running(args.manager), "items": []}
    started = time.perf_counter()
    try:
        loaded = api(args.manager, "/api/instances/silero-vad/load", "POST")
        result["load"] = {"ok": bool(loaded.get("ok")),
                          "wall_s": round(time.perf_counter() - started, 3),
                          "manager_total_ms": loaded.get("total_ms")}
    except Exception as error:
        result["load"] = {"ok": False, "error": read_error(error)}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return 1
    total_s = 0.0
    for item in manifest["items"]:
        wav = data / item["path"]
        request_started = time.perf_counter()
        record = {"ordinal": item["ordinal"], "id": item["id"],
                  "duration_s": item["duration_s"]}
        try:
            response = multipart(args.manager + "/v1/audio/speech-segments",
                                 {"model": "silero-vad"}, wav.name, wav.read_bytes())
            elapsed = time.perf_counter() - request_started
            segments = response.get("segments") or []
            total_s += elapsed
            record.update({"ok": True, "inference_s": round(elapsed, 6),
                           "segments": segments,
                           "detected_speech_s": round(sum(max(0, segment["end"] - segment["start"])
                                                          for segment in segments), 6)})
        except Exception as error:
            record.update({"ok": False, "error": read_error(error)})
        result["items"].append(record)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    duration_s = manifest["audio_duration_s"]
    result["summary"] = {
        "requests": len(result["items"]),
        "successful": sum(bool(item["ok"]) for item in result["items"]),
        "audio_duration_s": duration_s,
        "inference_s": round(total_s, 3),
        "real_time_factor": round(total_s / duration_s, 6),
        "audio_seconds_per_second": round(duration_s / total_s, 3) if total_s else None,
    }
    try:
        api(args.manager, "/api/instances/silero-vad/unload", "POST", 300)
    except Exception as error:
        result["unload_error"] = read_error(error)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
