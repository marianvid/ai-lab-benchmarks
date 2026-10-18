#!/usr/bin/env python3
"""Run the fixed OmniVoice voice-cloning benchmark from a local checkpoint."""

from __future__ import annotations

import sys
from pathlib import Path

import torch

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.tts.runners.omnivoice_runner import OmniVoiceRunner
from harness.shared.runs import peak_of, sha256, torch_facts


class OmniVoiceClone(OmniVoiceRunner):
    """OmniVoice cloning the reference voice from its clip and transcript."""

    reference = True

    def generate(self, _index: int, case: dict) -> dict:
        """One case in the cloned voice."""
        return self.spoken(
            case, language="Romanian" if case["language"] == "ro" else "English",
            ref_audio=str(self.reference_path), ref_text=self.args.reference_text)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, inputs, timings and platform."""
        return {
            "schema_version": 1, "engine": "omnivoice", "model_path": str(self.model_path),
            "manifest_sha256": sha256(self.manifest_path),
            "reference_sha256": sha256(self.reference_path),
            "reference_text": self.args.reference_text, "steps": self.args.steps,
            "load_s": round(self.load_s, 6), "load_vram_bytes": self.load_vram,
            "peak_vram_bytes": peak_of(records), **torch_facts(torch),
        }


if __name__ == "__main__":
    raise SystemExit(OmniVoiceClone().main())
