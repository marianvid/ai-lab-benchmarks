#!/usr/bin/env python3
"""Predict speech naturalness with the UTMOS22 strong learner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.speech_eval import generated, mono, spread

PREDICTOR = "tarepan/SpeechMOS:v1.2.0"
GROUP_KEYS = ("gender", "speaker")


def grouped(cases: list[dict]) -> dict:
    """Mean MOS per gender and per speaker, for the cases that say which."""
    groups = {}
    for key in GROUP_KEYS:
        labels = sorted({case[key] for case in cases if key in case})
        if labels:
            groups[f"by_{key}"] = {
                label: round(sum(case["mos"] for case in cases if case.get(key) == label)
                             / sum(case.get(key) == label for case in cases), 6)
                for label in labels}
    return groups


def summary(cases: list[dict]) -> dict:
    """Spread of MOS overall, per mode and per group."""
    by_mode = {}
    for mode in sorted({case["mode"] for case in cases}):
        values = [case["mos"] for case in cases if case["mode"] == mode]
        by_mode[mode] = round(sum(values) / len(values), 6)
    values = [case["mos"] for case in cases]
    return {**spread(values), "by_mode": by_mode, **grouped(cases),
            "completed": len(values), "cases": cases}


def main() -> int:
    """Predict MOS for every generated file of every run folder given."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    predictor = torch.hub.load(PREDICTOR, "utmos22_strong", trust_repo=True).to(device)
    predictor.device = device
    output: dict = {"schema_version": 1, "metric": "UTMOS22-strong",
                    "predictor": PREDICTOR, "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        cases = []
        for case, path in generated(root):
            samples, rate = mono(path)
            audio = torch.from_numpy(samples).unsqueeze(0).to(device)
            with torch.inference_mode():
                score = float(predictor(audio, rate).cpu().item())
            row = {"id": case["id"], "language": case["language"],
                   "mode": case.get("mode", "default"), "mos": round(score, 6)}
            row.update({key: case[key] for key in ("speaker", "gender") if key in case})
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        output["models"][root.name] = summary(cases)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
