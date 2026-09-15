#!/usr/bin/env python3
"""Expose held-out LibriTTS recordings in the same result schema as generated audio."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data, out = Path(args.data).resolve(), Path(args.out).resolve()
    audio_out = out / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    cases = []
    for source in manifest["cases"]:
        destination = audio_out / f"{source['id']}.wav"
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        os.symlink(data / source["target_audio"], destination)
        cases.append({**source, "ok": True, "audio_duration_s": source["target_duration_s"],
                      "sha256": source["target_sha256"], "source": "original-recording"})
    result = {"schema_version": 1, "benchmark": "libritts-test-clean-en100-v1",
              "engine": "ground-truth", "cases": cases}
    (out / "raw.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
