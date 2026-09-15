#!/usr/bin/env python3
"""Run the fixed Fish Speech HTTP voice-cloning benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import ormsgpack
import requests
import soundfile as sf

from fish_speech.utils.file import audio_to_bytes
from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpu_memory_bytes() -> int | None:
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=False,
    )
    values = []
    for line in result.stdout.splitlines():
        try:
            values.append(int(line.strip()) * 1024 * 1024)
        except ValueError:
            pass
    return sum(values) if values else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8188/v1/tts")
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reference-audio", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    reference_path = Path(args.reference_audio).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]

    reference = ServeReferenceAudio(
        audio=audio_to_bytes(str(reference_path)), text=args.reference_text,
    )
    records = []
    for case in cases:
        destination = audio_out / f"{case['id']}.wav"
        record = {"id": case["id"], "language": case["language"],
                  "text": case["text"], "ok": False}
        try:
            request = ServeTTSRequest(
                text=case["text"], references=[reference], format="wav",
                seed=args.seed, normalize=True, streaming=False,
            )
            before = time.perf_counter()
            response = requests.post(
                args.url, params={"format": "msgpack"},
                data=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                headers={"content-type": "application/msgpack"}, timeout=900,
            )
            elapsed = time.perf_counter() - before
            response.raise_for_status()
            destination.write_bytes(response.content)
            info = sf.info(destination)
            record.update({
                "ok": True,
                "seconds": round(elapsed, 6),
                "audio_duration_s": round(info.duration, 6),
                "rtf": round(elapsed / info.duration, 6),
                "sample_rate": info.samplerate,
                "sha256": sha256(destination),
                "gpu_process_memory_bytes": gpu_memory_bytes(),
            })
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    result = {
        "schema_version": 1,
        "engine": "fish-speech-http",
        "model_path": str(model_path),
        "manifest_sha256": sha256(manifest_path),
        "reference_sha256": sha256(reference_path),
        "reference_text": args.reference_text,
        "seed": args.seed,
        "server_startup_vram_bytes": 22210000000,
        "platform": platform.platform(),
        "cases": records,
    }
    (out / "raw.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
