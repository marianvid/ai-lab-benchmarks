#!/usr/bin/env python3
"""Prepare a deterministic Romanian FLEURS slice without redistributing it.

The converted Hugging Face parquet stores each audio file as bytes. This tool
selects rows evenly across the official test split, normalises them to mono
16 kHz PCM WAV with ffmpeg, and records only provenance and references in a
manifest. The WAV files stay in the data-preparation container and must not be committed.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import tempfile

import pyarrow.parquet as parquet


# The converted parquet's address, kept with the other sets' (`../datasets.json`).
SOURCE = json.loads((pathlib.Path(__file__).resolve().parents[1] / "datasets.json")
                    .read_text())["downloads"]["fleurs_ro_parquet"]
DATASET = "google/fleurs"
CONFIG = "ro_ro"
SPLIT = "test"
LICENSE = "CC-BY-4.0"


def evenly_spaced(total: int, wanted: int) -> list[int]:
    """`wanted` row indices spread evenly over `total` rows."""
    if wanted <= 0 or wanted > total:
        raise ValueError(f"limit must be between 1 and {total}")
    return [index * total // wanted for index in range(wanted)]


def audio_bytes(value: object) -> bytes:
    """The WAV bytes FLEURS embeds in its audio column."""
    if isinstance(value, dict) and isinstance(value.get("bytes"), bytes):
        return value["bytes"]
    raise ValueError("FLEURS audio column does not contain embedded bytes")


def duration(path: pathlib.Path) -> float:
    """A recording's length in seconds, as ffprobe reads it."""
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True)
    return float(completed.stdout.strip())


def extract(table, row_index: int, ordinal: int, out: pathlib.Path) -> dict:
    """One row as mono 16 kHz WAV under `out/audio`, and its manifest entry."""
    row = table.slice(row_index, 1).to_pylist()[0]
    identifier = str(row.get("id") or row_index)
    wav = out / "audio" / f"{ordinal:04d}-{identifier}.wav"
    with tempfile.NamedTemporaryFile(suffix=".audio") as encoded:
        encoded.write(audio_bytes(row["audio"]))
        encoded.flush()
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", encoded.name,
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
            check=True)
    return {
        "ordinal": ordinal, "source_row": row_index, "id": identifier,
        "path": str(wav.relative_to(out)), "duration_s": round(duration(wav), 6),
        "reference": row.get("transcription") or row.get("raw_transcription") or "",
        "speaker_id": row.get("speaker_id"), "gender": row.get("gender"),
    }


def main() -> int:
    """Extract the evenly spaced recordings and write their `MANIFEST.json`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet")
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    source = pathlib.Path(args.parquet)
    out = pathlib.Path(args.out)
    (out / "audio").mkdir(parents=True, exist_ok=True)
    table = parquet.read_table(source)
    rows = [extract(table, row_index, ordinal, out)
            for ordinal, row_index in enumerate(evenly_spaced(table.num_rows, args.limit))]
    manifest = {
        "schema_version": 1,
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "source": SOURCE,
        "license": LICENSE,
        "selection": "evenly spaced rows: floor(i * total_rows / limit)",
        "total_rows": table.num_rows,
        "selected_rows": len(rows),
        "audio_duration_s": round(sum(row["duration_s"] for row in rows), 3),
        "normalization": "ffmpeg mono 16 kHz PCM signed 16-bit WAV",
        "items": rows,
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in manifest.items() if key != "items"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
