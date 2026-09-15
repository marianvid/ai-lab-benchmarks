#!/usr/bin/env python3
"""Measure text/audio embedding similarity for generated sound effects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import librosa
import soundfile as sf
import torch
import torch.nn.functional as functional
from transformers import ClapModel, ClapProcessor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--model", default="laion/clap-htsat-unfused")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.result).resolve()
    raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = ClapProcessor.from_pretrained(args.model)
    model = ClapModel.from_pretrained(args.model).to(device).eval()
    sample_rate = int(processor.feature_extractor.sampling_rate)

    records = []
    for case in raw["cases"]:
        if not case.get("ok"):
            continue
        path = root / "audio" / f"{case['id']}.wav"
        audio, source_rate = sf.read(path, dtype="float32", always_2d=True)
        mono = audio.mean(axis=1)
        if source_rate != sample_rate:
            mono = librosa.resample(mono, orig_sr=source_rate, target_sr=sample_rate)
        inputs = processor(
            text=[case["prompt"]],
            audios=[mono],
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model(**inputs)
            similarity = float(functional.cosine_similarity(
                output.audio_embeds, output.text_embeds,
            ).item())
        row = {"id": case["id"], "category": case["category"],
               "cosine_similarity": round(similarity, 6)}
        records.append(row)
        print(json.dumps(row), flush=True)

    values = [row["cosine_similarity"] for row in records]
    report = {
        "schema_version": 1,
        "metric": "CLAP text-audio cosine similarity",
        "evaluator": args.model,
        "note": "Higher means closer in this embedding space; this is not a calibrated quality score.",
        "mean": round(sum(values) / len(values), 6),
        "min": min(values),
        "max": max(values),
        "completed": len(records),
        "cases": records,
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
