#!/usr/bin/env python3
"""Run Chatterbox Turbo with a native-English reference clip."""

from __future__ import annotations

import sys
from pathlib import Path

import soundfile as sf
import torch
from chatterbox.tts_turbo import ChatterboxTurboTTS

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import SEED, Runner, sha256, torch_facts


class ChatterboxTurbo(Runner):
    """Chatterbox Turbo speaking each case with the reference clip as the voice."""

    takes_model = False
    trace = True

    def options(self, parser) -> None:
        """--reference: the native-English clip whose voice is used."""
        parser.add_argument("--reference", required=True)

    def load(self):
        """The published checkpoint, on the card."""
        return ChatterboxTurboTTS.from_pretrained(device="cuda")

    def start(self, index: int, case: dict) -> dict:
        """The case, what it should say, and its seed."""
        return {"id": case["id"], "category": case["category"], "language": "en",
                "text": case["text"], "expected_text": case["expected_text"],
                "seed": SEED + index}

    def generate(self, index: int, case: dict) -> dict:
        """One case, seeded, written as 24-bit WAV."""
        self.seed(index)
        # Chatterbox's loudness-normalization path can promote the NumPy
        # reference to float64; the acoustic tokenizer expects float32.
        audio, elapsed = self.timed(lambda: self.model.generate(
            case["text"], audio_prompt_path=str(Path(self.args.reference).resolve()),
            norm_loudness=False))
        destination = self.destination(case)
        sf.write(destination, audio.detach().float().cpu().numpy().T, self.model.sr,
                 subtype="PCM_24")
        return self.measured(destination, elapsed, channels=True, process_rss=False)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, inputs, timings and platform."""
        return {"schema_version": 1, "engine": "chatterbox-turbo",
                "model": "ResembleAI/chatterbox-turbo", "device": "cuda",
                "reference_sha256": sha256(Path(self.args.reference).resolve()),
                "manifest_sha256": sha256(self.manifest_path),
                "load_s": round(self.load_s, 6), "load_vram_bytes": self.load_vram,
                **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(ChatterboxTurbo().main())
