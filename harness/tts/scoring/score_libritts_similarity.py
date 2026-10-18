#!/usr/bin/env python3
"""Score generated LibriTTS voices against held-out and enrollment audio."""

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

METRICS = ("generated_to_target", "generated_to_reference", "target_to_reference")


def average(cases: list[dict], metric: str, key: str, value: str) -> float:
    """The metric's mean over the cases whose `key` is `value`."""
    rows = [row[metric] for row in cases if row[key] == value]
    return round(sum(rows) / len(rows), 6)


def summarize(cases: list[dict]) -> dict:
    """Each metric's spread overall, per gender and per speaker."""
    result: dict = {"completed": len(cases), "cases": cases}
    for metric in METRICS:
        result[metric] = {
            **spread([row[metric] for row in cases]),
            "by_gender": {gender: average(cases, metric, "gender", gender)
                          for gender in ("F", "M")},
            "by_speaker": {speaker: average(cases, metric, "speaker", speaker)
                           for speaker in sorted({row["speaker"] for row in cases})},
        }
    return result


class Voices:
    """Speaker embeddings, each file embedded once."""

    def __init__(self, pipeline: str) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.embedding = PretrainedSpeakerEmbedding(Pipeline.from_pretrained(pipeline).embedding,
                                                    device=self.device)
        self.cache: dict = {}

    def vector(self, path: Path):
        """The embedding of one audio file."""
        key = str(path.resolve())
        if key not in self.cache:
            with torch.inference_mode():
                self.cache[key] = self.embedding(
                    waveform(path, self.embedding.sample_rate).to(self.device))[0]
        return self.cache[key]

    def compare(self, case: dict, path: Path, target: Path, reference: Path) -> dict:
        """The three similarities for one generated case."""
        made, held_out, enrolled = self.vector(path), self.vector(target), self.vector(reference)
        return {
            "id": case["id"], "speaker": case["speaker"], "gender": case["gender"],
            "generated_to_target": round(cosine(made, held_out), 6),
            "generated_to_reference": round(cosine(made, enrolled), 6),
            "target_to_reference": round(cosine(held_out, enrolled), 6),
        }


def main() -> int:
    """Compare every generated voice with its speaker's held-out and enrollment audio."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = Path(args.data).resolve()

    voices = Voices(args.pipeline)
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    references = {row["id"]: data / row["reference"]["audio"]
                  for row in manifest["speakers"]}
    output: dict = {"schema_version": 1, "metric": "cosine-speaker-similarity",
                    "evaluator": "pyannote/wespeaker-voxceleb-resnet34-LM",
                    "dataset": "LibriTTS test-clean", "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        cases = []
        for case, path in generated(root):
            row = voices.compare(case, path, data / case["target_audio"],
                                 references[case["speaker"]])
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        output["models"][root.name] = summarize(cases)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
