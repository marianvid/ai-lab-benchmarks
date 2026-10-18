#!/usr/bin/env python3
"""Run the fixed Fish Speech HTTP voice-cloning benchmark.

Fish Speech runs as its own HTTP server; its address is the setting
`benchmark.fish_tts_url` in AI-Lab's configuration (see `../../shared/lab.py`), unless
`--url` names another.
"""

from __future__ import annotations

import platform
import sys
import time
from pathlib import Path

import ormsgpack
import requests
from fish_speech.utils.file import audio_to_bytes
from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.lab import setting
from harness.shared.runs import SEED, Runner, gpu_memory_bytes, sha256, written_audio

# What the Fish server held on the card once started, measured by hand when
# this run was made (the server runs outside this script).
SERVER_STARTUP_VRAM_BYTES = 22_210_000_000
REQUEST_TIMEOUT_S = 900


def speak(url: str, request: ServeTTSRequest, destination: Path) -> float:
    """One request to the Fish server, the WAV saved; the seconds it took."""
    before = time.perf_counter()
    response = requests.post(
        url, params={"format": "msgpack"},
        data=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
        headers={"content-type": "application/msgpack"}, timeout=REQUEST_TIMEOUT_S)
    elapsed = time.perf_counter() - before
    response.raise_for_status()
    destination.write_bytes(response.content)
    return elapsed


class FishClone(Runner):
    """Fish Speech, through its own HTTP server, cloning the reference voice."""

    reference = True

    def options(self, parser) -> None:
        """--url (else the setting) and --seed."""
        parser.add_argument("--url", help="the Fish server's /v1/tts address "
                                          "(default: setting benchmark.fish_tts_url)")
        parser.add_argument("--seed", type=int, default=SEED)

    def load_timed(self) -> None:
        """Nothing loads here: the server holds the model. Read the reference once."""
        self.url = self.args.url or setting("fish_tts_url")
        self.reference_audio = ServeReferenceAudio(
            audio=audio_to_bytes(str(self.reference_path)), text=self.args.reference_text)

    def generate(self, _index: int, case: dict) -> dict:
        """One case from the server."""
        destination = self.destination(case)
        request = ServeTTSRequest(text=case["text"], references=[self.reference_audio],
                                  format="wav", seed=self.args.seed, normalize=True,
                                  streaming=False)
        elapsed = speak(self.url, request, destination)
        return {**written_audio(destination, elapsed),
                "gpu_process_memory_bytes": gpu_memory_bytes()}

    def facts(self, records: list[dict]) -> dict:
        """The checkpoint, inputs, the server's memory at start, and the platform."""
        return {"schema_version": 1, "engine": "fish-speech-http",
                "model_path": str(self.model_path), "manifest_sha256": sha256(self.manifest_path),
                "reference_sha256": sha256(self.reference_path),
                "reference_text": self.args.reference_text, "seed": self.args.seed,
                "server_startup_vram_bytes": SERVER_STARTUP_VRAM_BYTES,
                "platform": platform.platform()}


if __name__ == "__main__":
    raise SystemExit(FishClone().main())
