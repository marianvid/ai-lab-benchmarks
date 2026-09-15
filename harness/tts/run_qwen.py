#!/usr/bin/env python3
"""Run a reproducible Qwen3-TTS voice-cloning pass from a local checkpoint."""

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
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reference-audio", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    reference_path = Path(args.reference_audio).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]
    if args.limit is not None:
        cases = cases[:args.limit]

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
    prompt_started = time.perf_counter()
    voice_prompt = model.create_voice_clone_prompt(
        ref_audio=str(reference_path), ref_text=args.reference_text,
        x_vector_only_mode=False,
    )
    prompt_s = time.perf_counter() - prompt_started

    records = []
    for case in cases:
        record = {"id": case["id"], "language": case["language"],
                  "text": case["text"], "ok": False}
        destination = audio_out / f"{case['id']}.wav"
        try:
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            wavs, sample_rate = model.generate_voice_clone(
                text=case["text"], language=case.get("model_language", "Auto"),
                voice_clone_prompt=voice_prompt,
            )
            elapsed = time.perf_counter() - before
            sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
            info = sf.info(destination)
            record.update({
                "ok": True,
                "seconds": round(elapsed, 6),
                "audio_duration_s": round(info.duration, 6),
                "rtf": round(elapsed / info.duration, 6),
                "sample_rate": sample_rate,
                "sha256": sha256(destination),
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "rss_bytes": process.memory_info().rss,
            })
        except Exception as error:  # benchmark records failures verbatim
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    result = {
        "schema_version": 1,
        "engine": "qwen-tts",
        "model_path": str(model_path),
        "model_revision": (model_path / ".cache/huggingface/download/model.safetensors.metadata").read_text().strip()
        if (model_path / ".cache/huggingface/download/model.safetensors.metadata").exists() else None,
        "manifest_sha256": sha256(manifest_path),
        "reference_sha256": sha256(reference_path),
        "reference_text": args.reference_text,
        "load_s": round(load_s, 6),
        "voice_prompt_s": round(prompt_s, 6),
        "load_vram_bytes": load_vram,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "cases": records,
    }
    (out / "raw.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
