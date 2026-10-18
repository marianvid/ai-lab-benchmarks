#!/usr/bin/env python3
"""Run a reproducible Qwen3-TTS voice-cloning pass from a local checkpoint."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import psutil
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import Runner, sha256, torch_facts

# Where the Hugging Face download keeps the checkpoint's revision.
REVISION_FILE = ".cache/huggingface/download/model.safetensors.metadata"


def revision(model_path: Path) -> str | None:
    """The checkpoint's revision, as its download recorded it."""
    path = model_path / REVISION_FILE
    return path.read_text().strip() if path.exists() else None


class QwenClone(Runner):
    """Qwen3-TTS cloning the reference voice, the clone prompt made once."""

    reference = True

    def options(self, parser) -> None:
        """--limit: run only the first cases."""
        parser.add_argument("--limit", type=int)

    def load(self):
        """The checkpoint on the card in bfloat16."""
        self.process = psutil.Process()
        return Qwen3TTSModel.from_pretrained(str(self.model_path), device_map="cuda:0",
                                             dtype=torch.bfloat16, attn_implementation="sdpa")

    def load_timed(self) -> None:
        """Load, then make the voice prompt, timing each."""
        super().load_timed()
        started = time.perf_counter()
        self.voice_prompt = self.model.create_voice_clone_prompt(
            ref_audio=str(self.reference_path), ref_text=self.args.reference_text,
            x_vector_only_mode=False)
        self.prompt_s = time.perf_counter() - started

    def generate(self, _index: int, case: dict) -> dict:
        """One case in the cloned voice."""
        (wavs, sample_rate), elapsed = self.timed(lambda: self.model.generate_voice_clone(
            text=case["text"], language=case.get("model_language", "Auto"),
            voice_clone_prompt=self.voice_prompt))
        destination = self.destination(case)
        sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
        return self.measured(destination, elapsed)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, inputs, timings and platform."""
        return {
            "schema_version": 1, "engine": "qwen-tts", "model_path": str(self.model_path),
            "model_revision": revision(self.model_path),
            "manifest_sha256": sha256(self.manifest_path),
            "reference_sha256": sha256(self.reference_path),
            "reference_text": self.args.reference_text, "load_s": round(self.load_s, 6),
            "voice_prompt_s": round(self.prompt_s, 6), "load_vram_bytes": self.load_vram,
            "peak_vram_bytes": torch.cuda.max_memory_allocated(), **torch_facts(torch),
        }


if __name__ == "__main__":
    raise SystemExit(QwenClone().main())
