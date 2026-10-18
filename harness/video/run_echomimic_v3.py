#!/usr/bin/env python3
"""Run one reproducible EchoMimicV3 talking-head case."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time


MIB = 1048576
AUDIO_RATE = 16000      # what wav2vec2 was trained on


def options() -> argparse.Namespace:
    """The command line."""
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
    return parser.parse_args()


def benchmark_config(implementation, args, out: pathlib.Path) -> type:
    """The upstream settings, with this benchmark's paths and sizes laid over them.

    Built with `type()` because the class only exists once upstream is imported.
    """
    upstream_init = implementation.Config.__init__
    model_root = pathlib.Path(args.model_root).resolve()
    fixtures = pathlib.Path(args.fixtures).resolve()

    def benchmark_init(config) -> None:
        upstream_init(config)
        config.model_name = str(model_root / "Wan2.1-Fun-V1.1-1.3B-InP")
        config.transformer_path = str(
            model_root / "transformer" / "diffusion_pytorch_model.safetensors")
        config.wav2vec_model_dir = str(model_root / "wav2vec2-base-960h")
        config.base_dir = str(fixtures)
        config.test_name_list = [args.case]
        config.save_path = str(out)
        config.num_inference_steps = args.steps
        config.sample_size = [args.size, args.size]
        config.partial_video_length = 81
        config.overlap_video_length = 8
        config.seed = args.seed
        config.enable_teacache = False
    return type("BenchmarkConfig", (implementation.Config,), {"__init__": benchmark_init})


def profiling_once(torch, offload, profile_type, fraction: float):
    """A pipeline `.to()` that applies the memory profile the first time instead of moving."""
    profiled = False

    def profile_pipeline(pipeline, *_args, **_kwargs):
        nonlocal profiled
        if not profiled:
            budget_mb = int(
                torch.cuda.get_device_properties(0).total_memory / MIB * fraction)
            offload.profile(
                pipeline,
                profile_type.LowRAM_HighVRAM,
                budgets={"*": budget_mb},
                compile=False,
            )
            profiled = True
        return pipeline
    return profile_pipeline


def audio_features(librosa):
    """The upstream feature extractor, loading audio at wav2vec2's rate."""
    def extract_audio_features(audio_path, processor, model):
        audio_segment, sample_rate = librosa.load(audio_path, sr=AUDIO_RATE)
        input_values = processor(
            audio_segment, sampling_rate=sample_rate, return_tensors="pt"
        ).input_values.to(model.device)
        return model(input_values).last_hidden_state.squeeze(0)
    return extract_audio_features


def record_of(args, torch, out: pathlib.Path, outcome: dict) -> dict:
    """What was run, how it ended (`outcome`: status, error, wall_s) and the memory it took."""
    artifacts = sorted(out.glob(f"**/{args.case}_audio.mp4"),
                       key=lambda path: path.stat().st_mtime)
    return {
        "schema_version": 1,
        "model": "EchoMimicV3 preview 1.3B",
        "case": args.case,
        "status": outcome["status"],
        "error": outcome["error"],
        "wall_s": round(outcome["wall_s"], 3),
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


def main() -> int:
    """Run EchoMimic v3 on one case with this benchmark's settings, measured."""
    args = options()
    source = pathlib.Path(args.source).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(source))
    os.chdir(source)
    import infer_preview as implementation
    import librosa
    import torch
    from mmgp import offload, profile_type

    implementation.Config = benchmark_config(implementation, args, out)
    original_pipeline_to = implementation.WanFunInpaintAudioPipeline.to
    implementation.WanFunInpaintAudioPipeline.to = profiling_once(
        torch, offload, profile_type, args.max_vram_fraction)
    implementation.extract_audio_features = audio_features(librosa)
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
        record = record_of(args, torch, out, {"status": status, "error": error,
                                              "wall_s": time.perf_counter() - started})
        (out / f"{args.case}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        implementation.WanFunInpaintAudioPipeline.to = original_pipeline_to
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
