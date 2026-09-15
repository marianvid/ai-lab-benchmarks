#!/usr/bin/env python3
"""Run one TTS engine over the multi-speaker LibriTTS English suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import soundfile as sf

try:
    import psutil
except ImportError:  # Fish's minimal runtime does not need this optional metric.
    psutil = None


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
    parser.add_argument("--engine", required=True,
                        choices=("omnivoice", "qwen", "firered-base",
                                 "firered-instruct", "fish"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8188/v1/tts")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    manifest_path = Path(args.manifest).resolve()
    data = Path(args.data).resolve()
    out = Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    speakers = {row["id"]: row for row in manifest["speakers"]}
    cases = manifest["cases"][:args.limit] if args.limit else manifest["cases"]
    process = psutil.Process() if psutil else None
    records = []
    load_s = 0.0
    load_vram = None
    torch_version = cuda_version = gpu_name = None

    if args.engine != "fish":
        import torch
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        if args.engine == "qwen":
            from qwen_tts import Qwen3TTSModel
            model = Qwen3TTSModel.from_pretrained(
                str(model_path), device_map="cuda:0", dtype=torch.bfloat16,
                attn_implementation="sdpa")
        elif args.engine == "omnivoice":
            from omnivoice.models.omnivoice import OmniVoice
            model = OmniVoice.from_pretrained(
                str(model_path), device_map="cuda", dtype=torch.float16)
        elif args.engine == "firered-base":
            from fireredtts3.core import FireRedTTS3
            model = FireRedTTS3(str(model_path), use_fasttext=False,
                                use_llm_tn=False, use_wetext=False)
        else:
            from fireredtts3.core import FireRedTTS3Instruct
            model = FireRedTTS3Instruct(str(model_path), use_fasttext=False,
                                        use_llm_tn=False, use_wetext=False)
        load_s = time.perf_counter() - started
        load_vram = torch.cuda.memory_allocated()
        torch_version, cuda_version = torch.__version__, torch.version.cuda
        gpu_name = torch.cuda.get_device_name(0)
    else:
        import ormsgpack
        import requests
        from fish_speech.utils.file import audio_to_bytes
        from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest

    qwen_prompts = {}
    firered_refs = {}
    fish_refs = {}
    for case in cases:
        speaker = speakers[case["speaker"]]
        reference = speaker["reference"]
        reference_path = data / reference["audio"]
        destination = audio_out / f"{case['id']}.wav"
        record = {
            "id": case["id"], "speaker": case["speaker"],
            "gender": case["gender"], "language": "en", "text": case["text"],
            "target_audio": case["target_audio"],
            "target_sha256": case["target_sha256"],
            "reference_sha256": reference["sha256"], "ok": False,
        }
        try:
            if args.engine != "fish":
                torch.cuda.reset_peak_memory_stats()
            before = time.perf_counter()
            if args.engine == "qwen":
                if case["speaker"] not in qwen_prompts:
                    qwen_prompts[case["speaker"]] = model.create_voice_clone_prompt(
                        ref_audio=str(reference_path), ref_text=reference["text"],
                        x_vector_only_mode=False)
                wavs, sample_rate = model.generate_voice_clone(
                    text=case["text"], language="English",
                    voice_clone_prompt=qwen_prompts[case["speaker"]])
                sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
            elif args.engine == "omnivoice":
                wavs = model.generate(
                    text=case["text"], language="English", ref_audio=str(reference_path),
                    ref_text=reference["text"], num_step=32, guidance_scale=2.0)
                sf.write(destination, wavs[0], model.sampling_rate, subtype="PCM_16")
            elif args.engine.startswith("firered"):
                import torch
                import torchaudio
                if case["speaker"] not in firered_refs:
                    firered_refs[case["speaker"]] = torchaudio.load(reference_path)
                reference_audio, reference_rate = firered_refs[case["speaker"]]
                kwargs = dict(
                    prompt_text=reference["text"], prompt_audio=reference_audio,
                    prompt_audio_sr=reference_rate, text=case["text"],
                    language="English", do_tn=False)
                if args.engine == "firered-base":
                    waveform, sample_rate = model.generate(**kwargs)
                else:
                    waveform, sample_rate = model.generate_tts(**kwargs)
                torchaudio.save(str(destination), waveform.cpu(), sample_rate,
                                encoding="PCM_S", bits_per_sample=16)
            else:
                if case["speaker"] not in fish_refs:
                    fish_refs[case["speaker"]] = ServeReferenceAudio(
                        audio=audio_to_bytes(str(reference_path)), text=reference["text"])
                request = ServeTTSRequest(
                    text=case["text"], references=[fish_refs[case["speaker"]]],
                    format="wav", seed=args.seed, normalize=True, streaming=False)
                response = requests.post(
                    args.url, params={"format": "msgpack"},
                    data=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                    headers={"content-type": "application/msgpack"}, timeout=900)
                response.raise_for_status()
                destination.write_bytes(response.content)
            elapsed = time.perf_counter() - before
            info = sf.info(destination)
            record.update({
                "ok": True, "seconds": round(elapsed, 6),
                "audio_duration_s": round(info.duration, 6),
                "rtf": round(elapsed / info.duration, 6),
                "sample_rate": info.samplerate, "sha256": sha256(destination),
                "gpu_process_memory_bytes": gpu_memory_bytes(),
                "rss_bytes": process.memory_info().rss if process else None,
            })
            if args.engine != "fish":
                record["peak_vram_bytes"] = torch.cuda.max_memory_allocated()
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    result = {
        "schema_version": 1, "benchmark": "libritts-test-clean-en100-v1",
        "engine": args.engine, "model_path": str(model_path),
        "manifest_sha256": sha256(manifest_path), "seed": args.seed,
        "load_s": round(load_s, 6), "load_vram_bytes": load_vram,
        "peak_vram_bytes": max((r.get("peak_vram_bytes", 0) for r in records), default=None),
        "max_gpu_process_memory_bytes": max(
            (r.get("gpu_process_memory_bytes", 0) or 0 for r in records), default=None),
        "platform": platform.platform(), "python": platform.python_version(),
        "torch": torch_version, "cuda": cuda_version, "gpu": gpu_name,
        "settings": {"language": "English", "text_normalization": "disabled",
                     "omnivoice_steps": 32, "fish_seed": args.seed},
        "cases": records,
    }
    (out / "raw.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(record["ok"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
