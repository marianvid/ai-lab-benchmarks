"""What the automatic speech and sound scorers share: reading audio, comparing embeddings.

Imports torch, torchaudio and soundfile only when a function needs them, so a
scorer's environment needs only the libraries of the functions it calls.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def waveform(path: Path, sample_rate: int):
    """A file as a mono tensor at `sample_rate`, shaped (1, 1, samples)."""
    import torchaudio

    audio, rate = torchaudio.load(str(path))
    audio = audio.mean(dim=0, keepdim=True)
    if rate != sample_rate:
        audio = torchaudio.functional.resample(audio, rate, sample_rate)
    return audio.unsqueeze(0)


def mono(path: Path):
    """A file's samples averaged to one channel (float32), and its sample rate."""
    import soundfile as sf

    samples, rate = sf.read(path, dtype="float32", always_2d=True)
    return samples.mean(axis=1), rate


def cosine(left, right) -> float:
    """Cosine similarity of two embeddings, flattened."""
    import torch

    return torch.nn.functional.cosine_similarity(
        torch.as_tensor(left).flatten(), torch.as_tensor(right).flatten(), dim=0).item()


def spread(values: list[float]) -> dict:
    """Mean (six places), minimum and maximum."""
    return {"mean": round(sum(values) / len(values), 6), "min": min(values), "max": max(values)}


def generated(root: Path) -> Iterator[tuple[dict, Path]]:
    """Each successful case of a run folder, with its audio file."""
    raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
    for case in raw["cases"]:
        if case.get("ok"):
            yield case, root / "audio" / f"{case['id']}.wav"
