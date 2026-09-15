#!/usr/bin/env python3
"""Benchmark three Romanian character voices with OmniVoice voice design."""

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


PERSONAS = [
    {"id": "design-authoritative", "language": "ro",
     "text": "Omenirea nu are nevoie de o profeție, ci de o oglindă care spune adevărul fără să ridice vocea.",
     "instruction": "male, middle-aged, low pitch"},
    {"id": "design-empathetic", "language": "ro",
     "text": "Nu ești singur în fața schimbării. Putem înțelege împreună ce pierdem și ce alegem să păstrăm.",
     "instruction": "female, young adult, moderate pitch"},
    {"id": "design-warning", "language": "ro",
     "text": "Atenție. Puterea fără responsabilitate nu este progres; este o eroare care așteaptă să se întâmple.",
     "instruction": "female, middle-aged, very low pitch"},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=32)
    args = parser.parse_args()
    model_path, out = Path(args.model).resolve(), Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = OmniVoice.from_pretrained(str(model_path), device_map="cuda", dtype=torch.float16)
    load_s = time.perf_counter() - started
    records = []
    for case in PERSONAS:
        destination = audio_out / f"{case['id']}.wav"
        record = {**case, "mode": "voice-design", "ok": False}
        try:
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            wavs = model.generate(text=case["text"], language="Romanian",
                                  instruct=case["instruction"], num_step=args.steps,
                                  guidance_scale=2.0)
            elapsed = time.perf_counter() - before
            sf.write(destination, wavs[0], model.sampling_rate, subtype="PCM_16")
            info = sf.info(destination)
            record.update({"ok": True, "seconds": round(elapsed, 6),
                           "audio_duration_s": round(info.duration, 6),
                           "rtf": round(elapsed / info.duration, 6),
                           "sample_rate": info.samplerate, "sha256": sha256(destination),
                           "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                           "rss_bytes": process.memory_info().rss})
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    result = {"schema_version": 1, "engine": "omnivoice-voice-design",
              "model_path": str(model_path), "steps": args.steps,
              "load_s": round(load_s, 6),
              "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=0),
              "platform": platform.platform(), "python": platform.python_version(),
              "torch": torch.__version__, "cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0), "cases": records}
    (out / "raw.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
