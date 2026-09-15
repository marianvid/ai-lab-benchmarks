#!/usr/bin/env python3
"""Run the fixed OmniVoice voice-cloning benchmark from a local checkpoint."""

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
from omnivoice.models.omnivoice import OmniVoice


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
    parser.add_argument("--steps", type=int, default=32)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    reference_path = Path(args.reference_audio).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    process = psutil.Process()
    started = time.perf_counter()
    model = OmniVoice.from_pretrained(
        str(model_path), device_map="cuda", dtype=torch.float16,
    )
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()

    records = []
    for case in cases:
        destination = audio_out / f"{case['id']}.wav"
        record = {"id": case["id"], "language": case["language"],
                  "text": case["text"], "ok": False}
        try:
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            wavs = model.generate(
                text=case["text"],
                language="Romanian" if case["language"] == "ro" else "English",
                ref_audio=str(reference_path), ref_text=args.reference_text,
                num_step=args.steps, guidance_scale=2.0,
            )
            elapsed = time.perf_counter() - before
            sf.write(destination, wavs[0], model.sampling_rate, subtype="PCM_16")
            info = sf.info(destination)
            record.update({
                "ok": True,
                "seconds": round(elapsed, 6),
                "audio_duration_s": round(info.duration, 6),
                "rtf": round(elapsed / info.duration, 6),
                "sample_rate": info.samplerate,
                "sha256": sha256(destination),
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "rss_bytes": process.memory_info().rss,
            })
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    result = {
        "schema_version": 1,
        "engine": "omnivoice",
        "model_path": str(model_path),
        "manifest_sha256": sha256(manifest_path),
        "reference_sha256": sha256(reference_path),
        "reference_text": args.reference_text,
        "steps": args.steps,
        "load_s": round(load_s, 6),
        "load_vram_bytes": load_vram,
        "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=0),
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
