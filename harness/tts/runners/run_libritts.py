#!/usr/bin/env python3
"""Run one TTS engine over the multi-speaker LibriTTS English suite.

Each engine clones each LibriTTS speaker from that speaker's reference clip.
Four engines load in this process (on the card); Fish Speech runs as its own
HTTP server, whose address is `--url` or the setting `benchmark.fish_tts_url`
in AI-Lab's configuration (see `../../shared/lab.py`).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import soundfile as sf

try:
    import psutil
except ImportError:  # Fish's minimal runtime does not need this optional metric.
    psutil = None

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.lab import setting
from harness.shared.runs import (SEED, Runner, gpu_memory_bytes, load_on_card, peak_vram, sha256,
                         written_audio)

OMNIVOICE_STEPS = 32
FISH_TIMEOUT_S = 900


class Engine:
    """One engine: how it loads, and how it speaks a case in a speaker's voice."""

    on_card = True

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self.voices: dict = {}           # per speaker, whatever the engine prepares once

    def load(self):
        """Load the model (on the card, unless the engine runs elsewhere)."""
        raise NotImplementedError

    def speak(self, case: dict, reference: dict, reference_path: Path, destination: Path) -> None:
        """Write one case's audio to `destination`."""
        raise NotImplementedError


class Qwen(Engine):
    """Qwen3-TTS voice cloning, one clone prompt per speaker."""

    def load(self):
        """Load the model."""
        from qwen_tts import Qwen3TTSModel
        import torch
        self.model = Qwen3TTSModel.from_pretrained(
            str(self.model_path), device_map="cuda:0", dtype=torch.bfloat16,
            attn_implementation="sdpa")

    def speak(self, case, reference, reference_path, destination):
        """Write one case's audio in its speaker's voice."""
        if case["speaker"] not in self.voices:
            self.voices[case["speaker"]] = self.model.create_voice_clone_prompt(
                ref_audio=str(reference_path), ref_text=reference["text"],
                x_vector_only_mode=False)
        wavs, sample_rate = self.model.generate_voice_clone(
            text=case["text"], language="English", voice_clone_prompt=self.voices[case["speaker"]])
        sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")


class OmniVoiceEngine(Engine):
    """OmniVoice voice cloning from the reference clip and its text."""

    def load(self):
        """Load the model."""
        from omnivoice.models.omnivoice import OmniVoice
        import torch
        self.model = OmniVoice.from_pretrained(str(self.model_path), device_map="cuda",
                                               dtype=torch.float16)

    def speak(self, case, reference, reference_path, destination):
        """Write one case's audio in its speaker's voice."""
        wavs = self.model.generate(text=case["text"], language="English",
                                   ref_audio=str(reference_path), ref_text=reference["text"],
                                   num_step=OMNIVOICE_STEPS, guidance_scale=2.0)
        sf.write(destination, wavs[0], self.model.sampling_rate, subtype="PCM_16")


class FireRed(Engine):
    """FireRedTTS3, Base (`generate`) or Instruct (`generate_tts`)."""

    def __init__(self, model_path: Path, instruct: bool) -> None:
        super().__init__(model_path)
        self.instruct = instruct

    def load(self):
        """Load the model."""
        from fireredtts3.core import FireRedTTS3, FireRedTTS3Instruct
        kind = FireRedTTS3Instruct if self.instruct else FireRedTTS3
        self.model = kind(str(self.model_path), use_fasttext=False, use_llm_tn=False,
                          use_wetext=False)

    def speak(self, case, reference, reference_path, destination):
        """Write one case's audio in its speaker's voice."""
        import torchaudio
        if case["speaker"] not in self.voices:
            self.voices[case["speaker"]] = torchaudio.load(reference_path)
        reference_audio, reference_rate = self.voices[case["speaker"]]
        options = {"prompt_text": reference["text"], "prompt_audio": reference_audio,
                   "prompt_audio_sr": reference_rate, "text": case["text"],
                   "language": "English", "do_tn": False}
        call = self.model.generate_tts if self.instruct else self.model.generate
        waveform, sample_rate = call(**options)
        torchaudio.save(str(destination), waveform.cpu(), sample_rate,
                        encoding="PCM_S", bits_per_sample=16)


class Fish(Engine):
    """Fish Speech through its HTTP server, one reference per speaker."""

    on_card = False

    def __init__(self, model_path: Path, url: str, seed: int) -> None:
        super().__init__(model_path)
        self.url = url
        self.seed = seed

    def load(self):
        """Load the model."""
        return

    def speak(self, case, reference, reference_path, destination):
        """Write one case's audio in its speaker's voice."""
        import ormsgpack
        import requests
        from fish_speech.utils.file import audio_to_bytes
        from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest
        if case["speaker"] not in self.voices:
            self.voices[case["speaker"]] = ServeReferenceAudio(
                audio=audio_to_bytes(str(reference_path)), text=reference["text"])
        request = ServeTTSRequest(text=case["text"], references=[self.voices[case["speaker"]]],
                                  format="wav", seed=self.seed, normalize=True, streaming=False)
        response = requests.post(
            self.url, params={"format": "msgpack"},
            data=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
            headers={"content-type": "application/msgpack"}, timeout=FISH_TIMEOUT_S)
        response.raise_for_status()
        destination.write_bytes(response.content)


def engine_for(args: argparse.Namespace, model_path: Path) -> Engine:
    """The engine `--engine` names."""
    if args.engine == "qwen":
        return Qwen(model_path)
    if args.engine == "omnivoice":
        return OmniVoiceEngine(model_path)
    if args.engine.startswith("firered"):
        return FireRed(model_path, instruct=args.engine == "firered-instruct")
    return Fish(model_path, args.url or setting("fish_tts_url"), args.seed)


class LibriTTSRun(Runner):
    """Every LibriTTS case in its own speaker's cloned voice, with the engine `--engine` names."""

    def options(self, parser) -> None:
        """--engine, --data (the prepared subset), --url (Fish), --limit, --seed."""
        parser.add_argument("--engine", required=True,
                            choices=("omnivoice", "qwen", "firered-base", "firered-instruct",
                                     "fish"))
        parser.add_argument("--data", required=True)
        parser.add_argument("--url", help="Fish only: the server's /v1/tts address "
                                          "(default: setting benchmark.fish_tts_url)")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--seed", type=int, default=SEED)

    def load_timed(self) -> None:
        """The manifest's speakers, and the engine loaded (timed on the card)."""
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.speakers = {row["id"]: row for row in manifest["speakers"]}
        self.all_cases = manifest["cases"]
        self.data = Path(self.args.data).resolve()
        self.process = psutil.Process() if psutil else None
        self.engine = engine_for(self.args, self.model_path)
        self.versions = {"torch": None, "cuda": None, "gpu": None}
        self.load_vram = None
        if not self.engine.on_card:
            self.engine.load()
            return
        import torch
        _, self.load_s, self.load_vram = load_on_card(torch, self.engine.load)
        self.versions = {"torch": torch.__version__, "cuda": torch.version.cuda,
                         "gpu": torch.cuda.get_device_name(0)}

    def cases(self) -> list[dict]:
        """The manifest's cases, the first `--limit` when given."""
        return self.all_cases[:self.args.limit] if self.args.limit else self.all_cases

    def start(self, _index: int, case: dict) -> dict:
        """The case, its target recording and its speaker's reference."""
        return {"id": case["id"], "speaker": case["speaker"], "gender": case["gender"],
                "language": "en", "text": case["text"], "target_audio": case["target_audio"],
                "target_sha256": case["target_sha256"],
                "reference_sha256": self.speakers[case["speaker"]]["reference"]["sha256"]}

    def generate(self, _index: int, case: dict) -> dict:
        """One case; the time includes writing it, as the engines write their own files."""
        reference = self.speakers[case["speaker"]]["reference"]
        destination = self.destination(case)

        def speak() -> None:
            self.engine.speak(case, reference, self.data / reference["audio"], destination)
        if self.engine.on_card:
            _, elapsed = self.timed(speak)
        else:
            before = time.perf_counter()
            speak()
            elapsed = time.perf_counter() - before
        facts = {**written_audio(destination, elapsed),
                 "gpu_process_memory_bytes": gpu_memory_bytes(),
                 "rss_bytes": self.process.memory_info().rss if self.process else None}
        if self.engine.on_card:
            facts["peak_vram_bytes"] = peak_vram()
        return facts

    def facts(self, records: list[dict]) -> dict:
        """The benchmark, engine, timings, memory, platform and settings."""
        return {
            "schema_version": 1, "benchmark": "libritts-test-clean-en100-v1",
            "engine": self.args.engine, "model_path": str(self.model_path),
            "manifest_sha256": sha256(self.manifest_path), "seed": self.args.seed,
            "load_s": round(self.load_s, 6), "load_vram_bytes": self.load_vram,
            "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=None),
            "max_gpu_process_memory_bytes": max(
                (r.get("gpu_process_memory_bytes", 0) or 0 for r in records), default=None),
            "platform": platform.platform(), "python": platform.python_version(),
            **self.versions,
            "settings": {"language": "English", "text_normalization": "disabled",
                         "omnivoice_steps": OMNIVOICE_STEPS, "fish_seed": self.args.seed},
        }


if __name__ == "__main__":
    raise SystemExit(LibriTTSRun().main())
