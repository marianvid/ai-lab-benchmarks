#!/usr/bin/env python3
"""Measure cosine similarity to the reference speaker with local Pyannote/WeSpeaker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torchaudio
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding


def waveform(path: Path, sample_rate: int) -> torch.Tensor:
    audio, rate = torchaudio.load(str(path))
    audio = audio.mean(dim=0, keepdim=True)
    if rate != sample_rate:
        audio = torchaudio.functional.resample(audio, rate, sample_rate)
    return audio.unsqueeze(0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained(args.pipeline)
    embedding = PretrainedSpeakerEmbedding(pipeline.embedding, device=device)
    reference = waveform(Path(args.reference), embedding.sample_rate).to(device)
    with torch.inference_mode():
        reference_vector = embedding(reference)[0]

    output = {"schema_version": 1, "metric": "cosine-speaker-similarity",
              "evaluator": "pyannote/wespeaker-voxceleb-resnet34-LM",
              "reference": str(Path(args.reference).resolve()), "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
        cases = []
        for case in raw["cases"]:
            if not case.get("ok") or case.get("mode") == "voice-design":
                continue
            path = root / "audio" / f"{case['id']}.wav"
            with torch.inference_mode():
                vector = embedding(waveform(path, embedding.sample_rate).to(device))[0]
            similarity = torch.nn.functional.cosine_similarity(
                torch.as_tensor(reference_vector).flatten(),
                torch.as_tensor(vector).flatten(), dim=0,
            ).item()
            row = {"id": case["id"], "language": case["language"],
                   "similarity": round(similarity, 6)}
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        values = [case["similarity"] for case in cases]
        output["models"][root.name] = {
            "mean": round(sum(values) / len(values), 6),
            "min": min(values), "max": max(values), "completed": len(values),
            "cases": cases,
        }
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
