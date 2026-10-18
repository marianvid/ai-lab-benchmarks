#!/usr/bin/env python3
"""Run FireRedTTS3 Base voice cloning with the published default inference settings."""

from __future__ import annotations

import sys
from pathlib import Path

from fireredtts3.core import FireRedTTS3

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.tts.runners.firered import FireRedRunner


class FireRedBase(FireRedRunner):
    """FireRedTTS3 Base: cloning only."""

    engine = "fireredtts3-base"
    settings = {"n_timesteps": 10, "inference_cfg": 2.0,
                "text_normalization": "disabled; unsupported locally for Romanian"}

    def options(self, parser) -> None:
        """--limit: run only the first cases."""
        parser.add_argument("--limit", type=int)

    def model_class(self):
        """The Base model."""
        return FireRedTTS3

    def generate(self, _index: int, case: dict) -> dict:
        """One case in the cloned voice."""
        (waveform, sample_rate), elapsed = self.timed(
            lambda: self.model.generate(**self.clone_options(case)))
        return self.saved(case, waveform, sample_rate, elapsed)


if __name__ == "__main__":
    raise SystemExit(FireRedBase().main())
