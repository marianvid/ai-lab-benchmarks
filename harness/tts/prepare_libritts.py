#!/usr/bin/env python3
"""Prepare a deterministic, gender-balanced LibriTTS voice-cloning subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import wave
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def evenly(items: list, count: int) -> list:
    if len(items) < count:
        raise ValueError(f"need {count} items, found {len(items)}")
    if count == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def speaker_metadata(path: Path) -> dict[str, dict[str, str]]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(";"):
            continue
        fields = [field.strip() for field in line.split("|")]
        if len(fields) >= 4:
            rows[fields[0]] = {"gender": fields[1], "subset": fields[2]}
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    parser.add_argument("--speakers-per-gender", type=int, default=5)
    parser.add_argument("--targets-per-speaker", type=int, default=10)
    args = parser.parse_args()
    source, out = Path(args.source).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    metadata = speaker_metadata(source.parent / "SPEAKERS.txt")
    available = sorted(path.name for path in source.iterdir() if path.is_dir())
    by_speaker = {}
    for speaker in available:
        candidates = []
        for audio in sorted((source / speaker).rglob("*.wav")):
            text_path = audio.with_suffix(".normalized.txt")
            if not text_path.exists():
                continue
            text = text_path.read_text(encoding="utf-8").strip()
            seconds = duration(audio)
            candidates.append({"audio": audio, "text": text, "duration_s": seconds})
        eligible_refs = [row for row in candidates
                         if 6.0 <= row["duration_s"] <= 12.0
                         and 10 <= len(row["text"].split()) <= 45]
        eligible_targets = [row for row in candidates
                            if 2.5 <= row["duration_s"] <= 12.0
                            and 6 <= len(row["text"].split()) <= 45]
        if eligible_refs and len(eligible_targets) >= args.targets_per_speaker + 1:
            by_speaker[speaker] = candidates
    selected = []
    for gender in ("F", "M"):
        pool = [speaker for speaker in by_speaker
                if metadata.get(speaker, {}).get("gender") == gender]
        selected.extend(evenly(pool, args.speakers_per_gender))

    speakers, cases = [], []
    for speaker in selected:
        candidates = by_speaker[speaker]
        refs = [row for row in candidates
                if 6.0 <= row["duration_s"] <= 12.0 and 10 <= len(row["text"].split()) <= 45]
        reference = sorted(refs, key=lambda row: (abs(row["duration_s"] - 8.0), row["audio"].name))[0]
        targets = [row for row in candidates if row["audio"] != reference["audio"]
                   and 2.5 <= row["duration_s"] <= 12.0
                   and 6 <= len(row["text"].split()) <= 45]
        targets = evenly(sorted(targets, key=lambda row: row["audio"].name),
                         args.targets_per_speaker)
        speaker_out = out / speaker
        speaker_out.mkdir(parents=True, exist_ok=True)
        ref_name = "reference.wav"
        shutil.copy2(reference["audio"], speaker_out / ref_name)
        ref = {"audio": f"{speaker}/{ref_name}", "text": reference["text"],
               "duration_s": round(reference["duration_s"], 6),
               "source_id": reference["audio"].stem,
               "sha256": sha256(reference["audio"])}
        speakers.append({"id": speaker, "gender": metadata[speaker]["gender"],
                         "reference": ref})
        for index, target in enumerate(targets):
            target_name = f"target-{index:02d}.wav"
            shutil.copy2(target["audio"], speaker_out / target_name)
            cases.append({"id": f"spk-{speaker}-{index:02d}", "speaker": speaker,
                          "gender": metadata[speaker]["gender"], "language": "en",
                          "text": target["text"], "target_audio": f"{speaker}/{target_name}",
                          "target_duration_s": round(target["duration_s"], 6),
                          "target_source_id": target["audio"].stem,
                          "target_sha256": sha256(target["audio"])})
    manifest = {"schema_version": 1, "dataset": "LibriTTS", "subset": "test-clean",
                "archive_sha256": "234ea5b25859102a87024a4b9b86641f5b5aaaf1197335c95090cde04fe9a4f5",
                "selection": {"speakers_per_gender": args.speakers_per_gender,
                              "targets_per_speaker": args.targets_per_speaker,
                              "reference_duration_s": [6.0, 12.0],
                              "target_duration_s": [2.5, 12.0]},
                "speakers": speakers, "cases": cases}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"speakers": len(speakers), "cases": len(cases),
                      "female": sum(s["gender"] == "F" for s in speakers),
                      "male": sum(s["gender"] == "M" for s in speakers)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
