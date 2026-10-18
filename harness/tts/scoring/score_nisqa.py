#!/usr/bin/env python3
"""Score no-reference perceptual speech quality with NISQA v2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from torchmetrics.functional.audio.nisqa import non_intrusive_speech_quality_assessment

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.speech_eval import generated, mono

LABELS = ("mos", "noisiness", "discontinuity", "coloration", "loudness")


def score(case: dict, path: Path) -> dict:
    """NISQA's five scores for one file, or the error that stopped it."""
    samples, rate = mono(path)
    try:
        with torch.inference_mode():
            values = non_intrusive_speech_quality_assessment(
                torch.from_numpy(samples), rate).cpu().tolist()
    except Exception as error:
        return {"id": case["id"], "language": case["language"],
                "error": f"{type(error).__name__}: {error}"}
    return {"id": case["id"], "language": case["language"],
            **{key: round(float(value), 6) for key, value in zip(LABELS, values, strict=True)}}


def main() -> int:
    """Score every generated file of every run folder given; write one JSON file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output: dict = {"schema_version": 1, "metric": "NISQA-v2", "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        cases = []
        for case, path in generated(root):
            row = score(case, path)
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
