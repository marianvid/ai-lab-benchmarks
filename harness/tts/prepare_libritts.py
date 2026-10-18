#!/usr/bin/env python3
"""Prepare a deterministic, gender-balanced LibriTTS voice-cloning subset."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.runs import sha256

# What a reference clip and a target sentence may be: seconds, then words.
REFERENCE_SECONDS, REFERENCE_WORDS = (6.0, 12.0), (10, 45)
TARGET_SECONDS, TARGET_WORDS = (2.5, 12.0), (6, 45)
# The reference chosen is the eligible clip closest to this length.
IDEAL_REFERENCE_S = 8.0
ARCHIVE_SHA256 = "234ea5b25859102a87024a4b9b86641f5b5aaaf1197335c95090cde04fe9a4f5"
# A SPEAKERS.txt row: id | gender | subset | ...
METADATA_FIELDS = 4


@dataclass(frozen=True)
class Clip:
    """One LibriTTS utterance: its audio, its normalised text, its length."""

    audio: Path
    text: str
    duration_s: float

    def fits(self, seconds: tuple[float, float], words: tuple[int, int]) -> bool:
        """Whether its length and word count are within these bounds."""
        return (seconds[0] <= self.duration_s <= seconds[1]
                and words[0] <= len(self.text.split()) <= words[1])


def duration(path: Path) -> float:
    """A WAV file's length in seconds."""
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def evenly(items: list, count: int) -> list:
    """`count` items spread evenly over the list, first and last included."""
    if len(items) < count:
        raise ValueError(f"need {count} items, found {len(items)}")
    if count == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def speaker_metadata(path: Path) -> dict[str, dict[str, str]]:
    """SPEAKERS.txt: each speaker's gender and subset."""
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(";"):
            continue
        fields = [field.strip() for field in line.split("|")]
        if len(fields) >= METADATA_FIELDS:
            rows[fields[0]] = {"gender": fields[1], "subset": fields[2]}
    return rows


def clips_of(folder: Path) -> list[Clip]:
    """Every utterance of one speaker that has its normalised text beside it."""
    clips = []
    for audio in sorted(folder.rglob("*.wav")):
        text_path = audio.with_suffix(".normalized.txt")
        if text_path.exists():
            clips.append(Clip(audio, text_path.read_text(encoding="utf-8").strip(),
                              duration(audio)))
    return clips


def usable_speakers(source: Path, targets_per_speaker: int) -> dict[str, list[Clip]]:
    """Speakers with a reference clip and enough targets besides it."""
    usable = {}
    for speaker in sorted(path.name for path in source.iterdir() if path.is_dir()):
        clips = clips_of(source / speaker)
        has_reference = any(clip.fits(REFERENCE_SECONDS, REFERENCE_WORDS) for clip in clips)
        targets = [clip for clip in clips if clip.fits(TARGET_SECONDS, TARGET_WORDS)]
        if has_reference and len(targets) >= targets_per_speaker + 1:
            usable[speaker] = clips
    return usable


def choose(clips: list[Clip], targets_per_speaker: int) -> tuple[Clip, list[Clip]]:
    """A speaker's reference (closest to the ideal length) and evenly spread targets."""
    references = [clip for clip in clips if clip.fits(REFERENCE_SECONDS, REFERENCE_WORDS)]
    reference = sorted(references, key=lambda clip: (abs(clip.duration_s - IDEAL_REFERENCE_S),
                                                     clip.audio.name))[0]
    targets = [clip for clip in clips if clip.audio != reference.audio
               and clip.fits(TARGET_SECONDS, TARGET_WORDS)]
    return reference, evenly(sorted(targets, key=lambda clip: clip.audio.name),
                             targets_per_speaker)


def copy_speaker(out: Path, speaker: str, gender: str, picked: tuple[Clip, list[Clip]]
                 ) -> tuple[dict, list[dict]]:
    """Copy one speaker's reference and targets under `out`; its row and its cases."""
    reference, targets = picked
    speaker_out = out / speaker
    speaker_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reference.audio, speaker_out / "reference.wav")
    row = {"id": speaker, "gender": gender, "reference": {
        "audio": f"{speaker}/reference.wav", "text": reference.text,
        "duration_s": round(reference.duration_s, 6), "source_id": reference.audio.stem,
        "sha256": sha256(reference.audio)}}
    cases = []
    for index, target in enumerate(targets):
        target_name = f"target-{index:02d}.wav"
        shutil.copy2(target.audio, speaker_out / target_name)
        cases.append({"id": f"spk-{speaker}-{index:02d}", "speaker": speaker,
                      "gender": gender, "language": "en", "text": target.text,
                      "target_audio": f"{speaker}/{target_name}",
                      "target_duration_s": round(target.duration_s, 6),
                      "target_source_id": target.audio.stem,
                      "target_sha256": sha256(target.audio)})
    return row, cases


def main() -> int:
    """Choose the speakers, copy their clips, write `manifest.json`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    parser.add_argument("--speakers-per-gender", type=int, default=5)
    parser.add_argument("--targets-per-speaker", type=int, default=10)
    args = parser.parse_args()
    source, out = Path(args.source).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    metadata = speaker_metadata(source.parent / "SPEAKERS.txt")
    by_speaker = usable_speakers(source, args.targets_per_speaker)
    selected = []
    for gender in ("F", "M"):
        pool = [speaker for speaker in by_speaker
                if metadata.get(speaker, {}).get("gender") == gender]
        selected.extend(evenly(pool, args.speakers_per_gender))
    speakers, cases = [], []
    for speaker in selected:
        row, made = copy_speaker(out, speaker, metadata[speaker]["gender"],
                                 choose(by_speaker[speaker], args.targets_per_speaker))
        speakers.append(row)
        cases += made
    manifest = {"schema_version": 1, "dataset": "LibriTTS", "subset": "test-clean",
                "archive_sha256": ARCHIVE_SHA256,
                "selection": {"speakers_per_gender": args.speakers_per_gender,
                              "targets_per_speaker": args.targets_per_speaker,
                              "reference_duration_s": list(REFERENCE_SECONDS),
                              "target_duration_s": list(TARGET_SECONDS)},
                "speakers": speakers, "cases": cases}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"speakers": len(speakers), "cases": len(cases),
                      "female": sum(s["gender"] == "F" for s in speakers),
                      "male": sum(s["gender"] == "M" for s in speakers)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
