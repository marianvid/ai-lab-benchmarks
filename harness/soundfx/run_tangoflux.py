#!/usr/bin/env python3
"""Run TangoFlux on deterministic English sound-effect prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import time
from pathlib import Path

import soundfile as sf
import torch
from tangoflux import TangoFluxInference


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="declare-lab/TangoFlux")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--guidance-scale", type=float, default=4.5)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = TangoFluxInference(name=args.model, device="cuda")
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()

    records = []
    for index, case in enumerate(cases):
        destination = audio_out / f"{case['id']}.wav"
        seed = 20260915 + index
        record = {
            "id": case["id"],
            "category": case["category"],
            "prompt": case["prompt"],
            "duration_requested_s": case["duration_s"],
            "seed": seed,
            "ok": False,
        }
        try:
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            audio = model.generate(
                case["prompt"],
                steps=args.steps,
                duration=case["duration_s"],
                guidance_scale=args.guidance_scale,
            )
            elapsed = time.perf_counter() - before
            samples = audio.detach().float().cpu().numpy().T
            sf.write(destination, samples, 44100, subtype="PCM_24")
            info = sf.info(destination)
            record.update(
                {
                    "ok": True,
                    "seconds": round(elapsed, 6),
                    "audio_duration_s": round(info.duration, 6),
                    "rtf": round(elapsed / info.duration, 6),
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "sha256": sha256(destination),
                    "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                    "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                }
            )
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    raw = {
        "schema_version": 1,
        "engine": "tangoflux",
        "model": args.model,
        "device": "cuda",
        "steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "manifest_sha256": sha256(manifest_path),
        "load_s": round(load_s, 6),
        "load_vram_bytes": load_vram,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "cases": records,
    }
    (out / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(row["ok"] for row in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
