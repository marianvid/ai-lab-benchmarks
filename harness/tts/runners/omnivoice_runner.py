"""What the two OmniVoice runs share: the checkpoint, the step count, the saved file."""

from __future__ import annotations

import sys
from pathlib import Path

import psutil
import soundfile as sf
import torch
from omnivoice.models.omnivoice import OmniVoice

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import Runner

# The guidance both runs use.
GUIDANCE = 2.0


class OmniVoiceRunner(Runner):
    """An OmniVoice run: the checkpoint on the card in float16, `--steps` per case."""

    def options(self, parser) -> None:
        """--steps: diffusion steps per case."""
        parser.add_argument("--steps", type=int, default=32)

    def load(self):
        """The checkpoint on the card in float16."""
        self.process = psutil.Process()
        return OmniVoice.from_pretrained(str(self.model_path), device_map="cuda",
                                         dtype=torch.float16)

    def spoken(self, case: dict, **voice) -> dict:
        """Generate one case with these voice arguments, save it, and measure it."""
        wavs, elapsed = self.timed(lambda: self.model.generate(
            text=case["text"], num_step=self.args.steps, guidance_scale=GUIDANCE, **voice))
        destination = self.destination(case)
        sf.write(destination, wavs[0], self.model.sampling_rate, subtype="PCM_16")
        return self.measured(destination, elapsed)
