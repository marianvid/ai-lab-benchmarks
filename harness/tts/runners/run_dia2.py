#!/usr/bin/env python3
"""Run deterministic, prefix-conditioned Dia2 English dialogue cases."""

from __future__ import annotations

import sys
from pathlib import Path

import torch
from dia2 import Dia2, GenerationConfig, SamplingConfig

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import SEED, Runner, max_rss_bytes, sha256, torch_facts, written_audio


class Dia2Dialogue(Runner):
    """Dia2 speaking each two-speaker script, conditioned on its two example voices."""

    def options(self, parser) -> None:
        """--mimi: the Mimi codec checkpoint."""
        parser.add_argument("--mimi", required=True)

    def load(self):
        """Dia2 and its Mimi codec on the card, in bfloat16."""
        model = Dia2.from_local(
            config_path=self.model_path / "config.json",
            weights_path=self.model_path / "model.safetensors",
            device="cuda", dtype="bfloat16",
            tokenizer_id=self.model_path, mimi_id=str(Path(self.args.mimi).resolve()))
        self.config = GenerationConfig(text=SamplingConfig(temperature=0.6, top_k=50),
                                       audio=SamplingConfig(temperature=0.8, top_k=50),
                                       cfg_scale=2.0)
        return model

    def start(self, _index: int, case: dict) -> dict:
        """The dialogue: its transcript and its script."""
        return {"id": case["id"], "category": case["category"], "language": "en",
                "text": case["transcript"], "script": case["script"]}

    def generate(self, index: int, case: dict) -> dict:
        """One dialogue, seeded; Dia2 writes the WAV itself."""
        torch.manual_seed(SEED + index)
        destination = self.destination(case)
        result, elapsed = self.timed(lambda: self.model.generate(
            case["script"], config=self.config, output_wav=destination,
            prefix_speaker_1=str(self.model_path / "example_1.wav"),
            prefix_speaker_2=str(self.model_path / "example_2.wav"),
            include_prefix=False, verbose=False))
        return {**written_audio(destination, elapsed), "timestamps": result.timestamps,
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "max_rss_bytes": max_rss_bytes()}

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, timings and platform."""
        return {"schema_version": 2, "engine": "dia2", "model_path": str(self.model_path),
                "manifest_sha256": sha256(self.manifest_path), "load_s": round(self.load_s, 6),
                "load_vram_bytes": self.load_vram, **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(Dia2Dialogue().main())
