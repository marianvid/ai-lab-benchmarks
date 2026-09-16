#!/usr/bin/env python3
"""Run TA2.0 with fully local component paths for reproducible benchmarks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=path, required=True)
    parser.add_argument("--model-dir", type=path, required=True)
    parser.add_argument("--video-model-dir", type=path, required=True)
    parser.add_argument("--audio-model-dir", type=path, required=True)
    parser.add_argument("--image", type=path, required=True)
    parser.add_argument("--audio", type=path, required=True)
    parser.add_argument("--output", type=path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=832)
    parser.add_argument("--frames", type=int, default=77)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sys.path.insert(0, str(args.runtime_dir))
    from talking_avatar.config import GenerationConfig
    from talking_avatar.pipeline import TalkingAvatarPipeline

    config = GenerationConfig(
        width=args.width,
        height=args.height,
        frames=args.frames,
        steps=args.steps,
        seed=args.seed,
    )
    pipeline = TalkingAvatarPipeline.from_pretrained(
        args.model_dir,
        video_model_name_or_path=args.video_model_dir,
        audio_model_name_or_path=args.audio_model_dir,
        local_files_only=True,
        device="cuda",
    )
    result = pipeline.generate(
        image_path=args.image,
        audio_path=args.audio,
        prompt=args.prompt,
        output_path=args.output,
        config=config,
    )
    print(result)


if __name__ == "__main__":
    main()
