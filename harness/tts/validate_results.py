#!/usr/bin/env python3
"""Validate cross-file integrity of the published LibriTTS TTS results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MODELS = (
    "libritts-ground-truth-en100-v1", "libritts-omnivoice-en100-v1",
    "libritts-qwen-en100-v1", "libritts-firered-base-en100-v1",
    "libritts-firered-instruct-en100-v1", "libritts-fish-en100-v1",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    args = parser.parse_args()
    root = Path(args.results).resolve()
    manifest = json.loads((root / "libritts-en100-manifest.json").read_text())
    expected = {row["id"]: row for row in manifest["cases"]}
    assert len(expected) == 100
    assert len(manifest["speakers"]) == 10
    assert sum(row["gender"] == "F" for row in manifest["speakers"]) == 5
    assert sum(row["gender"] == "M" for row in manifest["speakers"]) == 5
    for model in MODELS:
        raw = json.loads((root / model / "raw.json").read_text())
        cases = {row["id"]: row for row in raw["cases"]}
        assert cases.keys() == expected.keys(), f"case mismatch: {model}"
        assert all(row.get("ok") for row in cases.values()), f"failed case: {model}"
        assert all(row["target_sha256"] == expected[case_id]["target_sha256"]
                   for case_id, row in cases.items()), f"target mismatch: {model}"
        assert len({row["sha256"] for row in cases.values()}) == 100, f"duplicate output: {model}"
    for filename in ("libritts-asr-whisper-large-v3-en.json",
                     "libritts-utmos22-strong.json", "libritts-speaker-similarity.json"):
        result = json.loads((root / filename).read_text())
        assert set(result["models"]) == set(MODELS), f"model mismatch: {filename}"
        for model in MODELS:
            assert result["models"][model]["completed"] == 100, f"incomplete: {filename}/{model}"
            assert {row["id"] for row in result["models"][model]["cases"]} == set(expected)
    print("validated: 10 speakers, 100 shared cases, 600 successful outputs, 1800 scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
