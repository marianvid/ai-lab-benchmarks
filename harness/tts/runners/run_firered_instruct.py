#!/usr/bin/env python3
"""Benchmark FireRedTTS3 Instruct voice cloning and three designed personas."""

from __future__ import annotations

import sys
from pathlib import Path

from fireredtts3.core import FireRedTTS3Instruct

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.tts.runners.firered import FireRedRunner, language_of
from harness.shared.runs import manifest_cases

PERSONAS = [
    {"id": "design-authoritative", "language": "ro",
     "text": "Omenirea nu are nevoie de o profeție, ci de o oglindă care spune adevărul fără să ridice vocea.",
     "instruction": "A calm, authoritative, gender-neutral narrator; mature, intelligent, low pitch, measured pace, restrained emotion."},
    {"id": "design-empathetic", "language": "ro",
     "text": "Nu ești singur în fața schimbării. Putem înțelege împreună ce pierdem și ce alegem să păstrăm.",
     "instruction": "A warm, empathetic adult voice; intimate but not sentimental, gentle pace, clear diction, subtle hope."},
    {"id": "design-warning", "language": "ro",
     "text": "Atenție. Puterea fără responsabilitate nu este progres; este o eroare care așteaptă să se întâmple.",
     "instruction": "A restrained urgent warning from a serious documentary narrator; controlled tension, precise articulation, no shouting."},
    {"id": "design-en-authoritative", "language": "en",
     "text": "Humanity does not need another prophecy. It needs a mirror that can tell the truth without raising its voice.",
     "instruction": "A calm, authoritative, gender-neutral narrator; mature, intelligent, low pitch, measured pace, restrained emotion."},
    {"id": "design-en-empathetic", "language": "en",
     "text": "You are not alone in facing change. We can decide together what to release and what deserves to remain.",
     "instruction": "A warm, empathetic adult voice; intimate but not sentimental, gentle pace, clear diction, subtle hope."},
    {"id": "design-en-warning", "language": "en",
     "text": "Warning. Power without responsibility is not progress; it is merely an error waiting to happen.",
     "instruction": "A restrained urgent warning from a serious documentary narrator; controlled tension, precise articulation, no shouting."},
]


class FireRedInstruct(FireRedRunner):
    """FireRedTTS3 Instruct: cloning every case, then designing every persona."""

    engine = "fireredtts3-instruct"
    settings = {"n_timesteps": 10, "clone_inference_cfg": 2.0,
                "design_inference_cfg": 1.2, "text_normalization": "disabled"}

    def model_class(self):
        """The Instruct model."""
        return FireRedTTS3Instruct

    def cases(self) -> list[dict]:
        """The manifest's cases to clone, then the personas to design."""
        return ([{**case, "mode": "clone"} for case in manifest_cases(self.manifest_path)]
                + [{**case, "mode": "voice-design"} for case in PERSONAS])

    def start(self, _index: int, case: dict) -> dict:
        """What the case says, how, and the persona's instruction."""
        record = {key: case[key] for key in ("id", "language", "text", "mode")}
        if "instruction" in case:
            record["instruction"] = case["instruction"]
        return record

    def speak(self, case: dict):
        """(waveform, sample rate, the plan a designed voice was made from, or None)."""
        if case["mode"] == "clone":
            waveform, sample_rate = self.model.generate_tts(**self.clone_options(case))
            return waveform, sample_rate, None
        return self.model.generate_voice_design(instruction=case["instruction"],
                                                text=case["text"], language=language_of(case),
                                                do_tn=False)

    def generate(self, _index: int, case: dict) -> dict:
        """One case cloned, or one persona designed."""
        (waveform, sample_rate, plan), elapsed = self.timed(lambda: self.speak(case))
        return {**self.saved(case, waveform, sample_rate, elapsed), "generated_plan": plan}


if __name__ == "__main__":
    raise SystemExit(FireRedInstruct().main())
