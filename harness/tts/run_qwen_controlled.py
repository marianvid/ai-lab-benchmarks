#!/usr/bin/env python3
"""Run Qwen3-TTS VoiceDesign or CustomVoice against English control cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import psutil
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("voice-design", "custom-voice"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    process = psutil.Process()
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(model_path), device_map="cuda:0", dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()
    records = []

    for case in cases:
        variants = [(None, case["voice_design"])] if args.mode == "voice-design" else [
            (speaker, case["custom_instruction"]) for speaker in case["custom_speakers"]
        ]
        for speaker, instruction in variants:
            output_id = case["id"] if speaker is None else f"{case['id']}--{speaker.lower()}"
            record = {
                "id": output_id, "case_id": case["id"], "category": case["category"],
                "language": "en", "model_language": "English", "text": case["text"], "speaker": speaker,
                "instruction": instruction, "ok": False,
            }
            destination = audio_out / f"{output_id}.wav"
            try:
                torch.cuda.reset_peak_memory_stats()
                before = time.perf_counter()
                if args.mode == "voice-design":
                    wavs, sample_rate = model.generate_voice_design(
                        text=case["text"], instruct=instruction, language="English")
                else:
                    wavs, sample_rate = model.generate_custom_voice(
                        text=case["text"], speaker=speaker, language="English",
                        instruct=instruction)
                elapsed = time.perf_counter() - before
                sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
                info = sf.info(destination)
                record.update({
                    "ok": True, "seconds": round(elapsed, 6),
                    "audio_duration_s": round(info.duration, 6),
                    "rtf": round(elapsed / info.duration, 6), "sample_rate": sample_rate,
                    "sha256": sha256(destination),
                    "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                    "rss_bytes": process.memory_info().rss,
                })
            except Exception as error:
                record["error"] = f"{type(error).__name__}: {error}"
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)

    result = {
        "schema_version": 2, "engine": "qwen-tts", "mode": args.mode,
        "model_path": str(model_path), "manifest_sha256": sha256(manifest_path),
        "load_s": round(load_s, 6), "load_vram_bytes": load_vram,
        "platform": platform.platform(), "python": platform.python_version(),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0), "cases": records,
    }
    (out / "raw.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if records and all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
