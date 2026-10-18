"""What the two FireRedTTS3 runners share: loading, language names, saving, run facts."""

from __future__ import annotations

import sys
from pathlib import Path

import psutil
import torch
import torchaudio

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.runs import Runner, peak_of, sha256, torch_facts


def language_of(case: dict) -> str:
    """The language name FireRedTTS3 takes for a case's language code."""
    return "Romanian" if case["language"] == "ro" else "English"


class FireRedRunner(Runner):
    """A FireRedTTS3 model cloning the reference voice; subclasses say which model."""

    reference = True
    engine = ""
    settings: dict = {}

    def model_class(self):
        """FireRedTTS3 or FireRedTTS3Instruct."""
        raise NotImplementedError

    def load_timed(self) -> None:
        """Read the reference voice first, so it is not counted as loading."""
        self.reference_audio, self.reference_rate = torchaudio.load(self.reference_path)
        self.process = psutil.Process()
        super().load_timed()

    def load(self):
        """The checkpoint, without the text normalisers it cannot use locally."""
        return self.model_class()(str(self.model_path), use_fasttext=False,
                                  use_llm_tn=False, use_wetext=False)

    def clone_options(self, case: dict) -> dict:
        """The arguments of a cloning call for one case."""
        return {"prompt_text": self.args.reference_text, "prompt_audio": self.reference_audio,
                "prompt_audio_sr": self.reference_rate, "text": case["text"],
                "language": language_of(case), "do_tn": False}

    def saved(self, case: dict, waveform, sample_rate: int, elapsed: float) -> dict:
        """Write the waveform as 16-bit WAV; its facts and the memory held."""
        destination = self.destination(case)
        torchaudio.save(str(destination), waveform.cpu(), sample_rate,
                        encoding="PCM_S", bits_per_sample=16)
        return self.measured(destination, elapsed)

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, inputs, settings, timings and platform."""
        return {
            "schema_version": 1, "engine": self.engine, "model_path": str(self.model_path),
            "manifest_sha256": sha256(self.manifest_path),
            "reference_sha256": sha256(self.reference_path),
            "reference_text": self.args.reference_text, "load_s": round(self.load_s, 6),
            "load_vram_bytes": self.load_vram, "peak_vram_bytes": peak_of(records),
            "settings": self.settings, **torch_facts(torch),
        }
