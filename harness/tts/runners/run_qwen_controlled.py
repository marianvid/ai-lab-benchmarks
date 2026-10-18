#!/usr/bin/env python3
"""Run Qwen3-TTS VoiceDesign or CustomVoice against English control cases."""

from __future__ import annotations

import sys
from pathlib import Path

import psutil
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import Runner, manifest_cases, sha256, torch_facts

DESIGN = "voice-design"


def variants(cases: list[dict], mode: str) -> list[dict]:
    """One entry per file to make: a case once (voice design) or once per speaker."""
    made = []
    for case in cases:
        pairs = ([(None, case["voice_design"])] if mode == DESIGN else
                 [(speaker, case["custom_instruction"]) for speaker in case["custom_speakers"]])
        for speaker, instruction in pairs:
            output_id = case["id"] if speaker is None else f"{case['id']}--{speaker.lower()}"
            made.append({"id": output_id, "case_id": case["id"], "category": case["category"],
                         "language": "en", "model_language": "English", "text": case["text"],
                         "speaker": speaker, "instruction": instruction})
    return made


class QwenControlled(Runner):
    """Qwen3-TTS VoiceDesign (a described voice) or CustomVoice (named speakers)."""

    def options(self, parser) -> None:
        """--mode: which of the two models this checkpoint is."""
        parser.add_argument("--mode", required=True, choices=(DESIGN, "custom-voice"))

    def load(self):
        """The checkpoint on the card in bfloat16."""
        self.process = psutil.Process()
        return Qwen3TTSModel.from_pretrained(str(self.model_path), device_map="cuda:0",
                                             dtype=torch.bfloat16, attn_implementation="sdpa")

    def cases(self) -> list[dict]:
        """Every file to make: each case once, or once per speaker."""
        return variants(manifest_cases(self.manifest_path), self.args.mode)

    def start(self, _index: int, case: dict) -> dict:
        """The variant as it was planned."""
        return dict(case)

    def speak(self, variant: dict):
        """(waveforms, sample rate) for one variant."""
        if self.args.mode == DESIGN:
            return self.model.generate_voice_design(
                text=variant["text"], instruct=variant["instruction"], language="English")
        return self.model.generate_custom_voice(
            text=variant["text"], speaker=variant["speaker"], language="English",
            instruct=variant["instruction"])

    def generate(self, _index: int, case: dict) -> dict:
        """One variant, written as 16-bit WAV."""
        (wavs, sample_rate), elapsed = self.timed(lambda: self.speak(case))
        destination = self.destination(case)
        sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
        return self.measured(destination, elapsed)

    def facts(self, records: list[dict]) -> dict:
        """The mode, checkpoint, timings and platform."""
        return {"schema_version": 2, "engine": "qwen-tts", "mode": self.args.mode,
                "model_path": str(self.model_path), "manifest_sha256": sha256(self.manifest_path),
                "load_s": round(self.load_s, 6), "load_vram_bytes": self.load_vram,
                **torch_facts(torch)}

    def main(self, argv: list[str] | None = None) -> int:
        """As every runner, but a run that made nothing failed too."""
        failed = super().main(argv)
        return failed if self.records else 1


if __name__ == "__main__":
    raise SystemExit(QwenControlled().main())
