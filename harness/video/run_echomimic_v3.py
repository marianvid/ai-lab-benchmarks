#!/usr/bin/env python3
"""Run one reproducible EchoMimicV3 talking-head case."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model-root", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=43)
    parser.add_argument("--max-vram-fraction", type=float, default=0.80)
    args = parser.parse_args()

    source = pathlib.Path(args.source).resolve()
    model_root = pathlib.Path(args.model_root).resolve()
    fixtures = pathlib.Path(args.fixtures).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(source))
    os.chdir(source)
    import infer_preview as implementation
    import librosa
    import torch
    from mmgp import offload, profile_type

    original_config = implementation.Config

    class BenchmarkConfig(original_config):
        def __init__(self):
            super().__init__()
            self.model_name = str(model_root / "Wan2.1-Fun-V1.1-1.3B-InP")
            self.transformer_path = str(
                model_root / "transformer" / "diffusion_pytorch_model.safetensors"
            )
            self.wav2vec_model_dir = str(model_root / "wav2vec2-base-960h")
            self.base_dir = str(fixtures)
            self.test_name_list = [args.case]
            self.save_path = str(out)
            self.num_inference_steps = args.steps
            self.sample_size = [args.size, args.size]
            self.partial_video_length = 81
            self.overlap_video_length = 8
            self.seed = args.seed
            self.enable_teacache = False

    implementation.Config = BenchmarkConfig
    original_pipeline_to = implementation.WanFunInpaintAudioPipeline.to
    profiled = False

    def profile_pipeline(pipeline, *unused_args, **unused_kwargs):
        nonlocal profiled
        if not profiled:
            budget_mb = int(
                torch.cuda.get_device_properties(0).total_memory
                / 1048576
                * args.max_vram_fraction
            )
            offload.profile(
                pipeline,
                profile_type.LowRAM_HighVRAM,
                budgets={"*": budget_mb},
                compile=False,
            )
            profiled = True
        return pipeline

    implementation.WanFunInpaintAudioPipeline.to = profile_pipeline

    def extract_audio_features(audio_path, processor, model):
        audio_segment, sample_rate = librosa.load(audio_path, sr=16000)
        input_values = processor(
            audio_segment, sampling_rate=sample_rate, return_tensors="pt"
        ).input_values.to(model.device)
        return model(input_values).last_hidden_state.squeeze(0)

    implementation.extract_audio_features = extract_audio_features
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    status = "succeeded"
    error = None
    try:
        implementation.main()
    except Exception as exc:
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        wall_s = time.perf_counter() - started
        artifacts = sorted(out.glob(f"**/{args.case}_audio.mp4"),
                           key=lambda path: path.stat().st_mtime)
        record = {
            "schema_version": 1,
            "model": "EchoMimicV3 preview 1.3B",
            "case": args.case,
            "status": status,
            "error": error,
            "wall_s": round(wall_s, 3),
            "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
            "settings": {
                "steps": args.steps,
                "size": [args.size, args.size],
                "fps": 25,
                "seed": args.seed,
                "weight_dtype": "bfloat16",
                "offload_profile": "LowRAM_HighVRAM",
                "max_vram_fraction": args.max_vram_fraction
            },
            "artifact": str(artifacts[-1]) if artifacts else None
        }
        (out / f"{args.case}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        implementation.WanFunInpaintAudioPipeline.to = original_pipeline_to
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
