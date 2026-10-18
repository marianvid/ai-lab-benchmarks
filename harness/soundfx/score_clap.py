#!/usr/bin/env python3
"""Measure text/audio embedding similarity for generated sound effects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import librosa
import torch
import torch.nn.functional as functional
from transformers import ClapModel, ClapProcessor

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.speech_eval import generated, mono, spread


class Clap:
    """The CLAP model and processor, on the card when there is one."""

    def __init__(self, name: str) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = ClapProcessor.from_pretrained(name)
        self.model = ClapModel.from_pretrained(name).to(self.device).eval()
        self.sample_rate = int(self.processor.feature_extractor.sampling_rate)

    def similarity(self, prompt: str, path: Path) -> float:
        """Cosine similarity of one sound file and its prompt."""
        samples, source_rate = mono(path)
        if source_rate != self.sample_rate:
            samples = librosa.resample(samples, orig_sr=source_rate,
                                       target_sr=self.sample_rate)
        inputs = self.processor(
            text=[prompt],
            audios=[samples],
            sampling_rate=self.sample_rate,
            return_tensors="pt",
            padding=True,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = self.model(**inputs)
            return float(functional.cosine_similarity(
                output.audio_embeds, output.text_embeds,
            ).item())


def main() -> int:
    """Compare each generated sound with its prompt in CLAP's shared space."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--model", default="laion/clap-htsat-unfused")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    clap = Clap(args.model)
    records = []
    for case, path in generated(Path(args.result).resolve()):
        row = {"id": case["id"], "category": case["category"],
               "cosine_similarity": round(clap.similarity(case["prompt"], path), 6)}
        records.append(row)
        print(json.dumps(row), flush=True)

    values = [row["cosine_similarity"] for row in records]
    report = {
        "schema_version": 1,
        "metric": "CLAP text-audio cosine similarity",
        "evaluator": args.model,
        "note": "Higher means closer in this embedding space; this is not a calibrated quality score.",
        **spread(values),
        "completed": len(records),
        "cases": records,
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
