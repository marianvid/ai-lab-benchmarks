#!/usr/bin/env python3
"""Measure cosine similarity to the reference speaker with local Pyannote/WeSpeaker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.speech_eval import cosine, generated, spread, waveform


def main() -> int:
    """Compare every cloned (not designed) voice with the one reference speaker."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained(args.pipeline)
    embedding = PretrainedSpeakerEmbedding(pipeline.embedding, device=device)

    def vector(path: Path):
        with torch.inference_mode():
            return embedding(waveform(path, embedding.sample_rate).to(device))[0]
    reference_vector = vector(Path(args.reference))
    output: dict = {"schema_version": 1, "metric": "cosine-speaker-similarity",
                    "evaluator": "pyannote/wespeaker-voxceleb-resnet34-LM",
                    "reference": str(Path(args.reference).resolve()), "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        cases = []
        for case, path in generated(root):
            if case.get("mode") == "voice-design":
                continue
            row = {"id": case["id"], "language": case["language"],
                   "similarity": round(cosine(reference_vector, vector(path)), 6)}
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        values = [case["similarity"] for case in cases]
        output["models"][root.name] = {**spread(values), "completed": len(values),
                                       "cases": cases}
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
