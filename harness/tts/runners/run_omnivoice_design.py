#!/usr/bin/env python3
"""Benchmark three Romanian character voices with OmniVoice voice design."""

from __future__ import annotations

import sys
from pathlib import Path

import torch

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.tts.runners.omnivoice_runner import OmniVoiceRunner
from harness.shared.runs import peak_of, torch_facts


PERSONAS = [
    {"id": "design-authoritative", "language": "ro",
     "text": "Omenirea nu are nevoie de o profeție, ci de o oglindă care spune adevărul fără să ridice vocea.",
     "instruction": "male, middle-aged, low pitch"},
    {"id": "design-empathetic", "language": "ro",
     "text": "Nu ești singur în fața schimbării. Putem înțelege împreună ce pierdem și ce alegem să păstrăm.",
     "instruction": "female, young adult, moderate pitch"},
    {"id": "design-warning", "language": "ro",
     "text": "Atenție. Puterea fără responsabilitate nu este progres; este o eroare care așteaptă să se întâmple.",
     "instruction": "female, middle-aged, very low pitch"},
]


class OmniVoiceDesign(OmniVoiceRunner):
    """OmniVoice making each persona's voice from its description alone."""

    takes_manifest = False

    def cases(self) -> list[dict]:
        """The three personas defined above."""
        return PERSONAS

    def start(self, _index: int, case: dict) -> dict:
        """The persona as defined."""
        return {**case, "mode": "voice-design"}

    def generate(self, _index: int, case: dict) -> dict:
        """One persona's line in its designed voice."""
        return self.spoken(case, language="Romanian", instruct=case["instruction"])

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, timings and platform."""
        return {"schema_version": 1, "engine": "omnivoice-voice-design",
                "model_path": str(self.model_path), "steps": self.args.steps,
                "load_s": round(self.load_s, 6), "peak_vram_bytes": peak_of(records),
                **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(OmniVoiceDesign().main())
