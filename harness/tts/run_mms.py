#!/usr/bin/env python3
"""Run the Romanian fixed-voice MMS-TTS baseline."""

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
from transformers import AutoTokenizer, VitsModel


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
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    cases = [case for case in json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]
             if case["language"] == "ro"]

    process = psutil.Process()
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = VitsModel.from_pretrained(str(model_path)).to("cuda")
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()
    records = []
    for case in cases:
        destination = audio_out / f"{case['id']}.wav"
        record = {"id": case["id"], "language": "ro", "text": case["text"], "ok": False}
        try:
            inputs = tokenizer(case["text"], return_tensors="pt").to("cuda")
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            with torch.inference_mode():
                waveform = model(**inputs).waveform[0].cpu().numpy()
            elapsed = time.perf_counter() - before
            sf.write(destination, waveform, model.config.sampling_rate, subtype="PCM_16")
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
    result = {"schema_version": 1, "engine": "transformers-vits",
              "model_path": str(model_path), "manifest_sha256": sha256(manifest_path),
              "load_s": round(load_s, 6), "load_vram_bytes": load_vram,
              "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=0),
              "platform": platform.platform(), "python": platform.python_version(),
              "torch": torch.__version__, "cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0), "cases": records}
    (out / "raw.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return 0 if all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
