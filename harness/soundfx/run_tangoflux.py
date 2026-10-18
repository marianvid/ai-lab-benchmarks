#!/usr/bin/env python3
"""Run TangoFlux on deterministic English sound-effect prompts."""

from __future__ import annotations

import sys
from pathlib import Path

import soundfile as sf
import torch
from tangoflux import TangoFluxInference

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.runs import SEED, Runner, sha256, torch_facts

SAMPLE_RATE = 44100


class TangoFlux(Runner):
    """TangoFlux on the card, one seeded clip per prompt."""

    takes_model = False

    def options(self, parser) -> None:
        """--model (default: the published checkpoint), --steps, --guidance-scale."""
        parser.add_argument("--model", default="declare-lab/TangoFlux")
        parser.add_argument("--steps", type=int, default=50)
        parser.add_argument("--guidance-scale", type=float, default=4.5)

    def load(self):
        """The checkpoint, on the card."""
        return TangoFluxInference(name=self.args.model, device="cuda")

    def start(self, index: int, case: dict) -> dict:
        """The prompt, the length asked for, and the seed."""
        return {"id": case["id"], "category": case["category"], "prompt": case["prompt"],
                "duration_requested_s": case["duration_s"], "seed": SEED + index}

    def generate(self, index: int, case: dict) -> dict:
        """One clip, seeded, written as 24-bit WAV."""
        self.seed(index)
        audio, elapsed = self.timed(lambda: self.model.generate(
            case["prompt"], steps=self.args.steps, duration=case["duration_s"],
            guidance_scale=self.args.guidance_scale))
        destination = self.destination(case)
        sf.write(destination, audio.detach().float().cpu().numpy().T, SAMPLE_RATE,
                 subtype="PCM_24")
        return self.measured(destination, elapsed, channels=True, process_rss=False)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, settings, timings and platform."""
        return {"schema_version": 1, "engine": "tangoflux", "model": self.args.model,
                "device": "cuda", "steps": self.args.steps,
                "guidance_scale": self.args.guidance_scale,
                "manifest_sha256": sha256(self.manifest_path), "load_s": round(self.load_s, 6),
                "load_vram_bytes": self.load_vram, **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(TangoFlux().main())
