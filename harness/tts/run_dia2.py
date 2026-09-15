#!/usr/bin/env python3
"""Run deterministic, prefix-conditioned Dia2 English dialogue cases."""

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
from dia2 import Dia2, GenerationConfig, SamplingConfig


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--mimi", required=True)
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
    started = time.perf_counter()
    model = Dia2.from_local(
        config_path=model_path / "config.json",
        weights_path=model_path / "model.safetensors",
        device="cuda", dtype="bfloat16",
        tokenizer_id=model_path, mimi_id=str(Path(args.mimi).resolve()),
    )
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()
    config = GenerationConfig(
        text=SamplingConfig(temperature=0.6, top_k=50),
        audio=SamplingConfig(temperature=0.8, top_k=50),
        cfg_scale=2.0,
    )
    prefix_1 = str(model_path / "example_1.wav")
    prefix_2 = str(model_path / "example_2.wav")
    records = []
    for index, case in enumerate(cases):
        torch.manual_seed(20260915 + index)
        destination = audio_out / f"{case['id']}.wav"
        record = {"id": case["id"], "category": case["category"], "language": "en",
                  "text": case["transcript"], "script": case["script"], "ok": False}
        try:
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            result = model.generate(
                case["script"], config=config, output_wav=destination,
                prefix_speaker_1=prefix_1, prefix_speaker_2=prefix_2,
                include_prefix=False, verbose=False,
            )
            elapsed = time.perf_counter() - before
            info = sf.info(destination)
            record.update({
                "ok": True, "seconds": round(elapsed, 6),
                "audio_duration_s": round(info.duration, 6),
                "rtf": round(elapsed / info.duration, 6), "sample_rate": info.samplerate,
                "sha256": sha256(destination), "timestamps": result.timestamps,
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            })
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    raw = {
        "schema_version": 2, "engine": "dia2", "model_path": str(model_path),
        "manifest_sha256": sha256(manifest_path), "load_s": round(load_s, 6),
        "load_vram_bytes": load_vram, "platform": platform.platform(),
        "python": platform.python_version(), "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0), "cases": records,
    }
    (out / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(row["ok"] for row in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
