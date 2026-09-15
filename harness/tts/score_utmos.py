#!/usr/bin/env python3
"""Predict speech naturalness with the UTMOS22 strong learner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torchaudio


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    predictor = torch.hub.load(
        "tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True,
    ).to(device)
    predictor.device = device
    output = {"schema_version": 1, "metric": "UTMOS22-strong",
              "predictor": "tarepan/SpeechMOS:v1.2.0", "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
        cases = []
        for case in raw["cases"]:
            if not case.get("ok"):
                continue
            path = root / "audio" / f"{case['id']}.wav"
            audio, rate = torchaudio.load(str(path))
            audio = audio.mean(dim=0, keepdim=True).to(device)
            with torch.inference_mode():
                score = float(predictor(audio, rate).cpu().item())
            row = {"id": case["id"], "language": case["language"],
                   "mode": case.get("mode", "default"), "mos": round(score, 6)}
            for key in ("speaker", "gender"):
                if key in case:
                    row[key] = case[key]
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        by_mode = {}
        for mode in sorted({case["mode"] for case in cases}):
            values = [case["mos"] for case in cases if case["mode"] == mode]
            by_mode[mode] = round(sum(values) / len(values), 6)
        values = [case["mos"] for case in cases]
        groups = {}
        for key in ("gender", "speaker"):
            labels = sorted({case[key] for case in cases if key in case})
            if labels:
                groups[f"by_{key}"] = {
                    label: round(sum(case["mos"] for case in cases if case.get(key) == label) /
                                 sum(case.get(key) == label for case in cases), 6)
                    for label in labels
                }
        output["models"][root.name] = {
            "mean": round(sum(values) / len(values), 6),
            "min": min(values), "max": max(values), "by_mode": by_mode,
            **groups, "completed": len(values), "cases": cases,
        }
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
