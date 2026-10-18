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


# The shape of the published set.
CASES = 100
SPEAKERS = 10
PER_GENDER = SPEAKERS // 2
SCORE_FILES = ("libritts-asr-whisper-large-v3-en.json",
               "libritts-utmos22-strong.json", "libritts-speaker-similarity.json")


class ResultsError(AssertionError):
    """The published results do not fit together."""


def require(condition: bool, message: str) -> None:
    """Raise `ResultsError` with `message` unless `condition` holds."""
    if not condition:
        raise ResultsError(message)


def check_manifest(manifest: dict) -> dict[str, dict]:
    """The manifest's cases by id, after checking its size and gender balance."""
    expected = {row["id"]: row for row in manifest["cases"]}
    require(len(expected) == CASES, f"the manifest has {len(expected)} cases")
    speakers = manifest["speakers"]
    require(len(speakers) == SPEAKERS, f"the manifest has {len(speakers)} speakers")
    for gender in ("F", "M"):
        require(sum(row["gender"] == gender for row in speakers) == PER_GENDER,
                f"the speakers are not {PER_GENDER} {gender}")
    return expected


def check_outputs(root: Path, model: str, expected: dict[str, dict]) -> None:
    """One model generated every case, against the right target, all different."""
    raw = json.loads((root / model / "raw.json").read_text())
    cases = {row["id"]: row for row in raw["cases"]}
    require(cases.keys() == expected.keys(), f"case mismatch: {model}")
    require(all(row.get("ok") for row in cases.values()), f"failed case: {model}")
    require(all(row["target_sha256"] == expected[case_id]["target_sha256"]
                for case_id, row in cases.items()), f"target mismatch: {model}")
    require(len({row["sha256"] for row in cases.values()}) == CASES,
            f"duplicate output: {model}")


def check_scores(root: Path, filename: str, expected: dict[str, dict]) -> None:
    """One score file covers every model and every case."""
    result = json.loads((root / filename).read_text())
    require(set(result["models"]) == set(MODELS), f"model mismatch: {filename}")
    for model in MODELS:
        scored = result["models"][model]
        require(scored["completed"] == CASES, f"incomplete: {filename}/{model}")
        require({row["id"] for row in scored["cases"]} == set(expected),
                f"case mismatch: {filename}/{model}")


def main() -> int:
    """Check that every model and score covers the same cases; raise `ResultsError` if not."""
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    args = parser.parse_args()
    root = Path(args.results).resolve()
    expected = check_manifest(json.loads((root / "libritts-en100-manifest.json").read_text()))
    for model in MODELS:
        check_outputs(root, model, expected)
    for filename in SCORE_FILES:
        check_scores(root, filename, expected)
    print(f"validated: {SPEAKERS} speakers, {CASES} shared cases, "
          f"{CASES * len(MODELS)} successful outputs, "
          f"{CASES * len(MODELS) * len(SCORE_FILES)} scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
