#!/usr/bin/env python3
"""Score generated LibriTTS voices against held-out and enrollment audio."""

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


def cosine(left, right) -> float:
    return torch.nn.functional.cosine_similarity(
        torch.as_tensor(left).flatten(), torch.as_tensor(right).flatten(), dim=0).item()


def summarize(cases: list[dict]) -> dict:
    result = {"completed": len(cases), "cases": cases}
    for metric in ("generated_to_target", "generated_to_reference", "target_to_reference"):
        values = [row[metric] for row in cases]
        result[metric] = {
            "mean": round(sum(values) / len(values), 6),
            "min": min(values), "max": max(values),
            "by_gender": {
                gender: round(sum(row[metric] for row in cases if row["gender"] == gender) /
                              sum(row["gender"] == gender for row in cases), 6)
                for gender in ("F", "M")
            },
            "by_speaker": {
                speaker: round(sum(row[metric] for row in cases if row["speaker"] == speaker) /
                               sum(row["speaker"] == speaker for row in cases), 6)
                for speaker in sorted({row["speaker"] for row in cases})
            },
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = Path(args.data).resolve()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained(args.pipeline)
    embedding = PretrainedSpeakerEmbedding(pipeline.embedding, device=device)
    cache = {}

    def vector(path: Path):
        key = str(path.resolve())
        if key not in cache:
            with torch.inference_mode():
                cache[key] = embedding(waveform(path, embedding.sample_rate).to(device))[0]
        return cache[key]

    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    references = {row["id"]: data / row["reference"]["audio"]
                  for row in manifest["speakers"]}
    output = {"schema_version": 1, "metric": "cosine-speaker-similarity",
              "evaluator": "pyannote/wespeaker-voxceleb-resnet34-LM",
              "dataset": "LibriTTS test-clean", "models": {}}
    for name in args.result:
        root = Path(name).resolve()
        raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
        cases = []
        for case in raw["cases"]:
            if not case.get("ok"):
                continue
            generated = vector(root / "audio" / f"{case['id']}.wav")
            target = vector(data / case["target_audio"])
            reference = vector(references[case["speaker"]])
            row = {
                "id": case["id"], "speaker": case["speaker"], "gender": case["gender"],
                "generated_to_target": round(cosine(generated, target), 6),
                "generated_to_reference": round(cosine(generated, reference), 6),
                "target_to_reference": round(cosine(target, reference), 6),
            }
            cases.append(row)
            print(json.dumps({"model": root.name, **row}), flush=True)
        output["models"][root.name] = summarize(cases)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
