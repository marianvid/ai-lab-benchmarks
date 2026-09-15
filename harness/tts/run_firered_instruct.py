#!/usr/bin/env python3
"""Benchmark FireRedTTS3 Instruct voice cloning and three designed personas."""

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
import torchaudio
from fireredtts3.core import FireRedTTS3Instruct


PERSONAS = [
    {"id": "design-authoritative", "language": "ro",
     "text": "Omenirea nu are nevoie de o profeție, ci de o oglindă care spune adevărul fără să ridice vocea.",
     "instruction": "A calm, authoritative, gender-neutral narrator; mature, intelligent, low pitch, measured pace, restrained emotion."},
    {"id": "design-empathetic", "language": "ro",
     "text": "Nu ești singur în fața schimbării. Putem înțelege împreună ce pierdem și ce alegem să păstrăm.",
     "instruction": "A warm, empathetic adult voice; intimate but not sentimental, gentle pace, clear diction, subtle hope."},
    {"id": "design-warning", "language": "ro",
     "text": "Atenție. Puterea fără responsabilitate nu este progres; este o eroare care așteaptă să se întâmple.",
     "instruction": "A restrained urgent warning from a serious documentary narrator; controlled tension, precise articulation, no shouting."},
    {"id": "design-en-authoritative", "language": "en",
     "text": "Humanity does not need another prophecy. It needs a mirror that can tell the truth without raising its voice.",
     "instruction": "A calm, authoritative, gender-neutral narrator; mature, intelligent, low pitch, measured pace, restrained emotion."},
    {"id": "design-en-empathetic", "language": "en",
     "text": "You are not alone in facing change. We can decide together what to release and what deserves to remain.",
     "instruction": "A warm, empathetic adult voice; intimate but not sentimental, gentle pace, clear diction, subtle hope."},
    {"id": "design-en-warning", "language": "en",
     "text": "Warning. Power without responsibility is not progress; it is merely an error waiting to happen.",
     "instruction": "A restrained urgent warning from a serious documentary narrator; controlled tension, precise articulation, no shouting."},
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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reference-audio", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    model_path, manifest_path = Path(args.model).resolve(), Path(args.manifest).resolve()
    reference_path, out = Path(args.reference_audio).resolve(), Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    clone_cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]
    reference_audio, reference_rate = torchaudio.load(reference_path)
    process = psutil.Process()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = FireRedTTS3Instruct(str(model_path), use_fasttext=False,
                                use_llm_tn=False, use_wetext=False)
    load_s = time.perf_counter() - started
    load_vram = torch.cuda.memory_allocated()
    records = []

    for source in [{**case, "mode": "clone"} for case in clone_cases] + [
            {**case, "mode": "voice-design"} for case in PERSONAS]:
        destination = audio_out / f"{source['id']}.wav"
        record = {key: source[key] for key in ("id", "language", "text", "mode")}
        record["ok"] = False
        if "instruction" in source:
            record["instruction"] = source["instruction"]
        try:
            torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            if source["mode"] == "clone":
                waveform, sample_rate = model.generate_tts(
                    prompt_text=args.reference_text, prompt_audio=reference_audio,
                    prompt_audio_sr=reference_rate, text=source["text"],
                    language="Romanian" if source["language"] == "ro" else "English",
                    do_tn=False,
                )
                generated_plan = None
            else:
                waveform, sample_rate, generated_plan = model.generate_voice_design(
                    instruction=source["instruction"], text=source["text"],
                    language="Romanian" if source["language"] == "ro" else "English",
                    do_tn=False,
                )
            elapsed = time.perf_counter() - before
            torchaudio.save(str(destination), waveform.cpu(), sample_rate,
                            encoding="PCM_S", bits_per_sample=16)
            info = sf.info(destination)
            record.update({"ok": True, "seconds": round(elapsed, 6),
                           "audio_duration_s": round(info.duration, 6),
                           "rtf": round(elapsed / info.duration, 6),
                           "sample_rate": info.samplerate, "sha256": sha256(destination),
                           "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                           "rss_bytes": process.memory_info().rss,
                           "generated_plan": generated_plan})
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    result = {"schema_version": 1, "engine": "fireredtts3-instruct",
              "model_path": str(model_path), "manifest_sha256": sha256(manifest_path),
              "reference_sha256": sha256(reference_path), "reference_text": args.reference_text,
              "load_s": round(load_s, 6), "load_vram_bytes": load_vram,
              "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=0),
              "settings": {"n_timesteps": 10, "clone_inference_cfg": 2.0,
                           "design_inference_cfg": 1.2, "text_normalization": "disabled"},
              "platform": platform.platform(), "python": platform.python_version(),
              "torch": torch.__version__, "cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0), "cases": records}
    (out / "raw.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return 0 if all(r["ok"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
