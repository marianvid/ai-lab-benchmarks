#!/usr/bin/env python3
"""Run the Romanian fixed-voice MMS-TTS baseline."""

from __future__ import annotations

import sys
from pathlib import Path

import psutil
import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import Runner, manifest_cases, peak_of, sha256, torch_facts


class MmsRomanian(Runner):
    """MMS-TTS, the fixed-voice Romanian baseline (no cloning)."""

    def load_timed(self) -> None:
        """Load the tokenizer and the model; the card's counters are not reset first."""
        import time

        self.process = psutil.Process()
        started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
        self.model = VitsModel.from_pretrained(str(self.model_path)).to("cuda")
        self.load_s = time.perf_counter() - started
        self.load_vram = torch.cuda.memory_allocated()

    def cases(self) -> list[dict]:
        """The manifest's Romanian cases."""
        return [case for case in manifest_cases(self.manifest_path) if case["language"] == "ro"]

    def start(self, _index: int, case: dict) -> dict:
        """The Romanian case."""
        return {"id": case["id"], "language": "ro", "text": case["text"]}

    def generate(self, _index: int, case: dict) -> dict:
        """One case, written as 16-bit WAV."""
        inputs = self.tokenizer(case["text"], return_tensors="pt").to("cuda")

        def speak():
            with torch.inference_mode():
                return self.model(**inputs).waveform[0].cpu().numpy()
        waveform, elapsed = self.timed(speak)
        destination = self.destination(case)
        sf.write(destination, waveform, self.model.config.sampling_rate, subtype="PCM_16")
        return self.measured(destination, elapsed)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, timings and platform."""
        return {"schema_version": 1, "engine": "transformers-vits",
                "model_path": str(self.model_path), "manifest_sha256": sha256(self.manifest_path),
                "load_s": round(self.load_s, 6), "load_vram_bytes": self.load_vram,
                "peak_vram_bytes": peak_of(records), **torch_facts(torch)}


if __name__ == "__main__":
    raise SystemExit(MmsRomanian().main())
