#!/usr/bin/env python3
"""Create a deterministic, per-case blinded TTS listening pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.runs import sha256


MODELS = {
    "human": "libritts-ground-truth-en100-v1",
    "omnivoice": "libritts-omnivoice-en100-v1",
    "qwen": "libritts-qwen-en100-v1",
    "firered-base": "libritts-firered-base-en100-v1",
    "firered-instruct": "libritts-firered-instruct-en100-v1",
    "fish": "libritts-fish-en100-v1",
}


# The page itself: a template, its style and its script (`listening/`). The
# pack's data goes beside them as `data.js`.
PAGE = Path(__file__).with_name("listening")
PAGE_FILES = ("index.html", "style.css", "app.js", "README.md")
SCALE = {"1": "unusable", "2": "poor", "3": "acceptable", "4": "good", "5": "excellent"}
# Cases 02 and 07 of each speaker: 20 prompts.
CHOSEN_SUFFIXES = ("-02", "-07")
CHOSEN_COUNT = 20


def shuffled(case_id: str) -> list[str]:
    """The candidates in this case's own order, the same on every run."""
    labels = list(MODELS)
    random.Random(int(hashlib.sha256(case_id.encode()).hexdigest()[:16], 16)).shuffle(labels)
    return labels


def blind_case(case: dict, results: Path, out: Path) -> tuple[list[dict], dict]:
    """Copy one case's six candidates under letters; (the public slots, slot -> model)."""
    case_out = out / "audio" / case["id"]
    case_out.mkdir()
    candidates, mapping = [], {}
    for index, label in enumerate(shuffled(case["id"])):
        slot = chr(ord("A") + index)
        destination = case_out / f"{slot}.wav"
        shutil.copy2(results / MODELS[label] / "audio" / f"{case['id']}.wav", destination,
                     follow_symlinks=True)
        candidates.append({"slot": slot, "audio": f"audio/{case['id']}/{slot}.wav",
                           "sha256": sha256(destination)})
        mapping[slot] = label
    return candidates, mapping


def copy_references(speakers: dict, data: Path, out: Path) -> dict[str, str]:
    """Each speaker's enrollment clip, copied; their checksums."""
    hashes = {}
    for speaker, row in speakers.items():
        destination = out / "references" / f"{speaker}.wav"
        shutil.copy2(data / row["reference"]["audio"], destination)
        hashes[speaker] = sha256(destination)
    return hashes


def write_page(out: Path, public: dict) -> None:
    """The page, its style and script, and the pack's data as `data.js`."""
    for name in PAGE_FILES:
        shutil.copy2(PAGE / name, out / name)
    (out / "data.js").write_text("const DATA = " + json.dumps(public) + ";\n", encoding="utf-8")


def main() -> int:
    """Write the blind listening pack: shuffled candidates, the page, the private reveal."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data, results, out = (Path(value).resolve() for value in (args.data, args.results, args.out))
    manifest = json.loads((data / "manifest.json").read_text())
    speakers = {row["id"]: row for row in manifest["speakers"]}
    chosen = [row for row in manifest["cases"] if row["id"].endswith(CHOSEN_SUFFIXES)]
    if len(chosen) != CHOSEN_COUNT:
        raise ValueError(f"expected {CHOSEN_COUNT} cases, found {len(chosen)}")
    if out.exists():
        shutil.rmtree(out)
    (out / "audio").mkdir(parents=True)
    (out / "references").mkdir()
    reference_hashes = copy_references(speakers, data, out)
    public_cases, reveal = [], {}
    for number, case in enumerate(chosen, 1):
        candidates, reveal[case["id"]] = blind_case(case, results, out)
        public_cases.append({"number": number, "id": case["id"], "speaker": case["speaker"],
                             "gender": case["gender"], "text": case["text"],
                             "reference_audio": f"references/{case['speaker']}.wav",
                             "reference_sha256": reference_hashes[case["speaker"]],
                             "candidates": candidates})
    public = {"schema_version": 1, "benchmark": "libritts-en-blind-listening-v1",
              "selection": "cases 02 and 07 for each of 10 speakers",
              "scale": SCALE, "cases": public_cases}
    (out / "manifest.json").write_text(json.dumps(public, indent=2) + "\n")
    (out / "private-reveal.json").write_text(json.dumps(reveal, indent=2) + "\n")
    write_page(out, public)
    print(json.dumps({"cases": len(public_cases), "candidates": len(public_cases) * 6,
                      "output": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
