#!/usr/bin/env python3
"""Score no-reference perceptual speech quality with NISQA v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import soundfile as sf
import torch
from torchmetrics.functional.audio.nisqa import non_intrusive_speech_quality_assessment


LABELS = ("mos", "noisiness", "discontinuity", "coloration", "loudness")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = {"schema_version": 1, "metric": "NISQA-v2", "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
        cases = []
        for case in raw["cases"]:
            if not case.get("ok"):
                continue
            path = root / "audio" / f"{case['id']}.wav"
            samples, rate = sf.read(path, dtype="float32", always_2d=True)
            audio = torch.from_numpy(samples.mean(axis=1))
            try:
                with torch.inference_mode():
                    values = non_intrusive_speech_quality_assessment(audio, rate).cpu().tolist()
                row = {"id": case["id"], "language": case["language"],
                       **{key: round(float(value), 6) for key, value in zip(LABELS, values)}}
            except Exception as error:
                row = {"id": case["id"], "language": case["language"],
                       "error": f"{type(error).__name__}: {error}"}
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        valid = [case for case in cases if "mos" in case]
        output["models"][root.name] = {
            "mean": {label: round(sum(case[label] for case in valid) / len(valid), 6)
                     for label in LABELS} if valid else {},
            "completed": len(valid), "cases": cases,
        }
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
