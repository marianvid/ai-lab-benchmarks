#!/usr/bin/env python3
"""Measure Romanian speaker diarization with reference RTTM annotations."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time
import wave

from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate

from run_asr import api, multipart, read_error, unload_running


MODELS = [
    {
        "instance": "diar-sortformer-4spk-v1",
        "model": "NVIDIA Sortformer 4-speaker v1",
        "engine": "NeMo",
        "license": "CC-BY-NC-4.0",
        "usage": "personal, non-commercial comparative evaluation only",
    },
    {
        "instance": "pyannote-community-1",
        "model": "Pyannote Speaker Diarization Community-1",
        "engine": "pyannote.audio",
        "license": "CC-BY-4.0",
    },
]


def duration(path: pathlib.Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def reference(path: pathlib.Path) -> Annotation:
    annotation = Annotation(uri=path.stem)
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 8 or fields[0] != "SPEAKER":
            raise ValueError(f"bad RTTM line {path}:{line_number}")
        start, length, speaker = float(fields[3]), float(fields[4]), fields[7]
        annotation[Segment(start, start + length), speaker] = speaker
    return annotation


def hypothesis(uri: str, segments: list[dict]) -> Annotation:
    annotation = Annotation(uri=uri)
    for item in segments:
        start, end = float(item["start"]), float(item["end"])
        speaker = str(item["speaker"])
        if end > start:
            annotation[Segment(start, end), speaker] = speaker
    return annotation


def score(metric: DiarizationErrorRate) -> dict:
    values = metric.accumulated_
    total = float(values.get("total", 0.0))
    missed = float(values.get("missed detection", 0.0))
    false_alarm = float(values.get("false alarm", 0.0))
    confusion = float(values.get("confusion", 0.0))
    return {
        "der": round((missed + false_alarm + confusion) / total, 6)
        if total else None,
        "reference_speaker_time_s": round(total, 6),
        "missed_detection_s": round(missed, 6),
        "false_alarm_s": round(false_alarm, 6),
        "speaker_confusion_s": round(confusion, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", default="http://192.168.50.222:8090")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", help="comma-separated instance ids")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    root = pathlib.Path(args.data)
    output = pathlib.Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    wanted = set(args.only.split(",")) if args.only else None
    pairs = []
    for condition in ("no_overlap", "overlap"):
        for audio in sorted((root / condition / "audio").glob("*.wav")):
            rttm = root / condition / "rttm" / f"{audio.stem}.rttm"
            if not rttm.is_file():
                raise FileNotFoundError(rttm)
            pairs.append((condition, audio, rttm))
    if args.limit:
        pairs = pairs[:args.limit]

    summary_path = output / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    for model in MODELS:
        instance = model["instance"]
        if wanted and instance not in wanted:
            continue
        entry = dict(model)
        entry.update({
            "dataset": "upb-nlp/echo-synthetic-diarization",
            "dataset_revision": "b627c5bf437937d90efafc7cf76d5dcfb3195f35",
            "language": "ro",
            "files": len(pairs),
            "metric": {"name": "DER", "collar_s": 0.25,
                       "score_overlap": True},
            "preload_unloads": unload_running(args.manager),
        })
        load_started = time.perf_counter()
        try:
            loaded = api(args.manager, f"/api/instances/{instance}/load", "POST")
            entry["load"] = {"ok": bool(loaded.get("ok")),
                             "wall_s": round(time.perf_counter() - load_started, 3),
                             "manager_total_ms": loaded.get("total_ms")}
            if not loaded.get("ok"):
                raise RuntimeError(loaded.get("error") or "load failed")
        except Exception as error:
            entry.setdefault("load", {"ok": False})
            entry["load"]["error"] = read_error(error)
            entry["status"] = "load_failed"
            summary[instance] = entry
            summary_path.write_text(json.dumps(summary, indent=2) + "\n")
            continue

        # Warm kernels and decoder state without including this request in speed.
        warm_audio = pairs[0][1]
        warm_started = time.perf_counter()
        try:
            multipart(args.manager + "/v1/audio/diarizations", {"model": instance},
                      warm_audio.name, warm_audio.read_bytes())
            entry["warmup"] = {"ok": True,
                               "wall_s": round(time.perf_counter() - warm_started, 6)}
        except Exception as error:
            entry["warmup"] = {"ok": False, "error": read_error(error)}

        overall = DiarizationErrorRate(collar=0.25, skip_overlap=False)
        conditions = {name: DiarizationErrorRate(collar=0.25, skip_overlap=False)
                      for name in ("no_overlap", "overlap")}
        records, inference_s, audio_s = [], 0.0, 0.0
        for position, (condition, audio, rttm) in enumerate(pairs, 1):
            length = duration(audio)
            record = {"id": audio.stem, "condition": condition,
                      "duration_s": round(length, 6),
                      "reference_speakers": int(re.search(r"_(\d+)spk$", audio.stem).group(1))}
            request_started = time.perf_counter()
            try:
                response = multipart(args.manager + "/v1/audio/diarizations",
                                     {"model": instance}, audio.name,
                                     audio.read_bytes())
                elapsed = time.perf_counter() - request_started
                segments = response.get("segments") or []
                expected = reference(rttm)
                actual = hypothesis(audio.stem, segments)
                uem = Timeline([Segment(0.0, length)], uri=audio.stem)
                details = overall(expected, actual, uem=uem, detailed=True)
                conditions[condition](expected, actual, uem=uem)
                inference_s += elapsed
                audio_s += length
                record.update({"ok": True, "inference_s": round(elapsed, 6),
                               "detected_speakers": len(set(response.get("speakers") or [])),
                               "der": round(float(details["diarization error rate"]), 6),
                               "segments": segments})
            except Exception as error:
                record.update({"ok": False, "error": read_error(error)})
            records.append(record)
            (output / f"{instance}.json").write_text(
                json.dumps({"schema_version": 1, "instance": instance,
                            "items": records}, ensure_ascii=False, indent=2) + "\n")
            print(f"{instance}: {position}/{len(pairs)} "
                  f"{'ok' if record['ok'] else 'FAILED'}", flush=True)

        entry.update({"status": "complete" if all(item["ok"] for item in records)
                      else "partial",
                      "successful": sum(bool(item["ok"]) for item in records),
                      "failed": sum(not item["ok"] for item in records),
                      "audio_duration_s": round(audio_s, 3),
                      "inference_s": round(inference_s, 3),
                      "real_time_factor": round(inference_s / audio_s, 6)
                      if audio_s else None,
                      "audio_seconds_per_second": round(audio_s / inference_s, 3)
                      if inference_s else None,
                      "score": score(overall),
                      "by_condition": {name: score(metric)
                                       for name, metric in conditions.items()}})
        try:
            unloaded = api(args.manager, f"/api/instances/{instance}/unload", "POST", 300)
            entry["unload"] = {"ok": bool(unloaded.get("ok")),
                               "manager_total_ms": unloaded.get("total_ms")}
        except Exception as error:
            entry["unload"] = {"ok": False, "error": read_error(error)}
        summary[instance] = entry
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({instance: entry["score"]}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
