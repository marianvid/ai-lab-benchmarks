#!/usr/bin/env python3
"""Run Stable Audio 3 on deterministic English sound-effect prompts."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from stable_audio_3 import StableAudioModel

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.runs import SEED, Runner, max_rss_bytes, sha256, torch_facts, written_audio


class StableAudio3(Runner):
    """Stable Audio 3 on the card or the processor, one seeded clip per prompt."""

    takes_model = False

    def options(self, parser) -> None:
        """--model (the published size), --device, --steps."""
        parser.add_argument("--model", required=True, choices=("small-sfx", "medium"))
        parser.add_argument("--device", required=True, choices=("cpu", "cuda"))
        parser.add_argument("--steps", type=int, default=8)

    @property
    def on_card(self) -> bool:
        """Whether this run uses the card (and so measures its memory)."""
        return self.args.device == "cuda"

    def load_timed(self) -> None:
        """Load on the chosen device; card memory is counted only on the card."""
        if self.on_card:
            super().load_timed()
            return
        started = time.perf_counter()
        self.model = self.load()
        self.load_s, self.load_vram = time.perf_counter() - started, 0

    def load(self):
        """The published model of that size."""
        return StableAudioModel.from_pretrained(self.args.model, device=self.args.device)

    def start(self, _index: int, case: dict) -> dict:
        """The prompt and the length asked for."""
        return {"id": case["id"], "category": case["category"], "prompt": case["prompt"],
                "duration_requested_s": case["duration_s"]}

    def generate(self, index: int, case: dict) -> dict:
        """One clip, seeded, written as 24-bit WAV."""
        if self.on_card:
            torch.cuda.reset_peak_memory_stats()
        before = time.perf_counter()
        audio = self.model.generate(prompt=case["prompt"], duration=case["duration_s"],
                                    steps=self.args.steps, cfg_scale=1.0, seed=SEED + index)
        elapsed = time.perf_counter() - before
        destination = self.destination(case)
        sf.write(destination, audio[0].detach().float().cpu().numpy().T,
                 self.model.model.sample_rate, subtype="PCM_24")
        return {**written_audio(destination, elapsed, channels=True),
                "peak_vram_bytes": torch.cuda.max_memory_allocated() if self.on_card else 0,
                "max_rss_bytes": max_rss_bytes()}

    def facts(self, records: list[dict]) -> dict:
        """The model, device, steps, timings and platform."""
        return {"schema_version": 1, "engine": "stable-audio-3", "model": self.args.model,
                "device": self.args.device, "steps": self.args.steps,
                "manifest_sha256": sha256(self.manifest_path), "load_s": round(self.load_s, 6),
                "load_vram_bytes": self.load_vram, **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(StableAudio3().main())
