#!/usr/bin/env python3
"""Measure Romanian speaker diarization with reference RTTM annotations."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import wave

from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from harness.shared.lab import MANAGER_HELP, manager_url, multipart, read_error, timed, unload_running

DIARIZATIONS = "/v1/audio/diarizations"
# Speech overlapping by less than this, at a boundary, is not counted (seconds).
COLLAR_S = 0.25
# An RTTM line: SPEAKER file channel start duration ... speaker ...
RTTM_FIELDS = 8
CONDITIONS = ("no_overlap", "overlap")


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
    """A WAV file's length in seconds."""
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def reference(path: pathlib.Path) -> Annotation:
    """Who speaks when, as the dataset's RTTM file says."""
    annotation = Annotation(uri=path.stem)
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) < RTTM_FIELDS or fields[0] != "SPEAKER":
            raise ValueError(f"bad RTTM line {path}:{line_number}")
        start, length, speaker = float(fields[3]), float(fields[4]), fields[7]
        annotation[Segment(start, start + length), speaker] = speaker
    return annotation


def hypothesis(uri: str, segments: list[dict]) -> Annotation:
    """Who speaks when, as the model answered."""
    annotation = Annotation(uri=uri)
    for item in segments:
        start, end = float(item["start"]), float(item["end"])
        speaker = str(item["speaker"])
        if end > start:
            annotation[Segment(start, end), speaker] = speaker
    return annotation


def score(metric: DiarizationErrorRate) -> dict:
    """The accumulated diarization error rate and its three parts, in seconds."""
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


def pairs_in(root: pathlib.Path, limit: int | None) -> list[tuple[str, pathlib.Path, pathlib.Path]]:
    """(condition, audio, its RTTM) for every recording, in order."""
    pairs = []
    for condition in CONDITIONS:
        for audio in sorted((root / condition / "audio").glob("*.wav")):
            rttm = root / condition / "rttm" / f"{audio.stem}.rttm"
            if not rttm.is_file():
                raise FileNotFoundError(rttm)
            pairs.append((condition, audio, rttm))
    return pairs[:limit] if limit else pairs


def speakers_in(stem: str) -> int:
    """The number of speakers a file name says it has (`..._3spk`)."""
    found = re.search(r"_(\d+)spk$", stem)
    if found is None:
        raise ValueError(f"no speaker count in {stem}")
    return int(found.group(1))


def outcome(records: list[dict]) -> dict:
    """How many recordings succeeded, and the speed over those that did."""
    done = [item for item in records if item["ok"]]
    inference_s = sum(item["inference_s"] for item in done)
    audio_s = sum(item["duration_s"] for item in done)
    return {
        "status": "complete" if len(done) == len(records) else "partial",
        "successful": len(done), "failed": len(records) - len(done),
        "audio_duration_s": round(audio_s, 3), "inference_s": round(inference_s, 3),
        "real_time_factor": round(inference_s / audio_s, 6) if audio_s else None,
        "audio_seconds_per_second": round(audio_s / inference_s, 3) if inference_s else None,
    }


class Study:
    """One run: the recordings, the manager, and where the results go."""

    def __init__(self, manager: str, pairs: list, output: pathlib.Path) -> None:
        self.manager = manager
        self.pairs = pairs
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.summary_path = output / "summary.json"
        self.summary = (json.loads(self.summary_path.read_text())
                        if self.summary_path.exists() else {})

    def diarize(self, instance: str, audio: pathlib.Path) -> dict:
        """One recording through the gateway."""
        return multipart(self.manager + DIARIZATIONS, {"model": instance},
                         ("file", audio.name, audio.read_bytes()))

    def save(self, instance: str, entry: dict) -> None:
        """Record one model's entry in the summary, at once."""
        self.summary[instance] = entry
        self.summary_path.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2) + "\n")

    def run_model(self, model: dict) -> None:
        """Load one model, warm it, diarize every recording, unload; record it all."""
        instance = model["instance"]
        entry = dict(model)
        entry.update({
            "dataset": "upb-nlp/echo-synthetic-diarization",
            "dataset_revision": "b627c5bf437937d90efafc7cf76d5dcfb3195f35",
            "language": "ro", "files": len(self.pairs),
            "metric": {"name": "DER", "collar_s": COLLAR_S, "score_overlap": True},
            "preload_unloads": unload_running(self.manager),
        })
        entry["load"] = timed(self.manager, instance, "load")
        if not entry["load"]["ok"]:
            entry["status"] = "load_failed"
            self.save(instance, entry)
            return
        entry["warmup"] = self.warm_up(instance)
        entry.update(self.diarize_all(instance))
        unloaded = timed(self.manager, instance, "unload")
        entry["unload"] = {key: unloaded[key] for key in ("ok", "manager_total_ms", "error")
                           if key in unloaded}
        self.save(instance, entry)
        print(json.dumps({instance: entry["score"]}, indent=2), flush=True)

    def warm_up(self, instance: str) -> dict:
        """Warm kernels and decoder state without including this request in speed."""
        started = time.perf_counter()
        try:
            self.diarize(instance, self.pairs[0][1])
            return {"ok": True, "wall_s": round(time.perf_counter() - started, 6)}
        except Exception as error:
            return {"ok": False, "error": read_error(error)}

    def diarize_all(self, instance: str) -> dict:
        """Every recording once, scored overall and per condition."""
        overall = DiarizationErrorRate(collar=COLLAR_S, skip_overlap=False)
        conditions = {name: DiarizationErrorRate(collar=COLLAR_S, skip_overlap=False)
                      for name in CONDITIONS}
        records: list[dict] = []
        for position, (condition, audio, rttm) in enumerate(self.pairs, 1):
            record = self.diarize_one(instance, audio, rttm, (overall, conditions[condition]))
            record["condition"] = condition
            records.append(record)
            (self.output / f"{instance}.json").write_text(json.dumps(
                {"schema_version": 1, "instance": instance, "items": records},
                ensure_ascii=False, indent=2) + "\n")
            print(f"{instance}: {position}/{len(self.pairs)} "
                  f"{'ok' if record['ok'] else 'FAILED'}", flush=True)
        return {
            **outcome(records), "score": score(overall),
            "by_condition": {name: score(metric) for name, metric in conditions.items()},
        }

    def diarize_one(self, instance: str, audio: pathlib.Path, rttm: pathlib.Path,
                    metrics: tuple[DiarizationErrorRate, DiarizationErrorRate]) -> dict:
        """One recording: diarized, scored into the overall and its condition's metric."""
        length = duration(audio)
        record: dict = {"id": audio.stem, "duration_s": round(length, 6),
                        "reference_speakers": speakers_in(audio.stem)}
        started = time.perf_counter()
        try:
            response = self.diarize(instance, audio)
            elapsed = time.perf_counter() - started
            segments = response.get("segments") or []
            expected, actual = reference(rttm), hypothesis(audio.stem, segments)
            uem = Timeline([Segment(0.0, length)], uri=audio.stem)
            details = metrics[0](expected, actual, uem=uem, detailed=True)
            metrics[1](expected, actual, uem=uem)
            record.update({"ok": True, "inference_s": round(elapsed, 6),
                           "detected_speakers": len(set(response.get("speakers") or [])),
                           "der": round(float(details["diarization error rate"]), 6),
                           "segments": segments})
        except Exception as error:
            record.update({"ok": False, "error": read_error(error)})
        return record


def main() -> int:
    """Run every model (or those in `--only`) and keep each outcome."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", help=MANAGER_HELP)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", help="comma-separated instance ids")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    study = Study(manager_url(args.manager), pairs_in(pathlib.Path(args.data), args.limit),
                  pathlib.Path(args.out))
    wanted = set(args.only.split(",")) if args.only else None
    for model in MODELS:
        if not wanted or model["instance"] in wanted:
            study.run_model(model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
