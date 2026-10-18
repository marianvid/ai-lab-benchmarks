#!/usr/bin/env python3
"""Generate docs/audio-results.md from the published raw audio results."""

from __future__ import annotations

import argparse
import json
import pathlib


ORDER = [
    "whisper-large-v3", "whisper-large-v3-turbo", "qwen3-asr-06b",
    "qwen3-asr-17b", "parakeet-tdt-06b-v3", "canary-1b-v2",
    "nemotron-35-asr-streaming-06b",
]


def number(value, digits=3, suffix="") -> str:
    """A figure to `digits` places with its unit, or a dash when there is none."""
    return "—" if value is None else f"{value:.{digits}f}{suffix}"


def read(path: pathlib.Path) -> dict:
    """A results file, or nothing when that part was not run."""
    return json.loads(path.read_text()) if path.exists() else {}


def asr_table(summary: dict) -> list[str]:
    """One row per ASR model: completion, error rates, load time and speed."""
    lines = [
        "| Model | Engine | Completed | [WER](glossary.md#wer) | [CER](glossary.md#cer) | WER without diacritics | Load (s) | [RTF](glossary.md#rtf) | [Audio × real time](glossary.md#rtf) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ORDER:
        item = summary.get(key, {})
        load = item.get("load", {})
        completed = ("unsupported" if item.get("status") == "warmup_failed" else
                     f"{item.get('successful', 0)}/{item.get('requests', item.get('selected_rows', 100))}"
                     if item else "not run")
        lines.append(
            f"| {item.get('model', key)} | {item.get('engine', '—')} | {completed} | "
            f"{number(item.get('wer'))} | {number(item.get('cer'))} | "
            f"{number(item.get('wer_without_diacritics'))} | "
            f"{number(load.get('wall_s'), 1)} | {number(item.get('real_time_factor'))} | "
            f"{number(item.get('audio_seconds_per_second'), 1, '×')} |")
    return lines


def failures(summary: dict) -> list[str]:
    """Every model that did not load, refused the warm-up, or failed requests."""
    found = []
    for key in ORDER:
        item = summary.get(key)
        if not item:
            found.append(f"- `{key}` has no result file.")
        elif not item.get("load", {}).get("ok"):
            found.append(f"- **{item.get('model', key)}** did not load: `{item['load'].get('error', 'unknown error')}`")
        elif item.get("status") == "warmup_failed":
            found.append(f"- **{item.get('model', key)}** loaded, then refused the Romanian warm-up. Its checkpoint lists only English, Spanish and Chinese prompt keys; no accuracy or speed result is claimed.")
        elif item.get("failed"):
            found.append(f"- **{item.get('model', key)}**: {item['failed']} of {item['requests']} requests failed; see `../results/audio/asr/details/{key}.json`.")
    return found or ["No load or transcription request failed."]


def vad_section(vad: dict) -> list[str]:
    """Silero's stability and throughput, or that it has no result."""
    summary = vad.get("summary") or {}
    if not summary:
        return ["Silero VAD has no completed result."]
    return [
        f"Silero VAD completed {summary.get('successful')}/{summary.get('requests')} requests in "
        f"{number(summary.get('inference_s'), 2, ' s')}, an RTF of "
        f"{number(summary.get('real_time_factor'), 5)} or "
        f"{number(summary.get('audio_seconds_per_second'), 1, '× real time')}.", "",
        "This is a technical stability and throughput result. FLEURS has no speech-boundary labels, so no VAD quality score is reported.",
    ]


def diarization_section(diarization: dict) -> list[str]:
    """DER per model, overall and with and without overlap."""
    if not diarization:
        return ["No diarization run has been recorded."]
    lines = [
        "Echo Synthetic Diarization contains 120 Romanian 60-second files "
        "with reference speaker turns: 60 without overlap and 60 with overlap. "
        "DER uses a 0.25 s collar and scores overlapped speech.", "",
        "| Model | Licence | Completed | [DER](glossary.md#der) | No-overlap DER | Overlap DER | Load (s) | [Audio × real time](glossary.md#rtf) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ("diar-sortformer-4spk-v1", "pyannote-community-1"):
        item = diarization.get(key, {})
        by = item.get("by_condition") or {}
        lines.append(
            f"| {item.get('model', key)} | {item.get('license', '—')} | "
            f"{item.get('successful', 0)}/{item.get('files', 120)} | "
            f"{number((item.get('score') or {}).get('der'))} | "
            f"{number((by.get('no_overlap') or {}).get('der'))} | "
            f"{number((by.get('overlap') or {}).get('der'))} | "
            f"{number((item.get('load') or {}).get('wall_s'), 1)} | "
            f"{number(item.get('audio_seconds_per_second'), 1, '×')} |")
    return lines + ["", "Lower DER is better. Sortformer is an NC-licensed "
                    "checkpoint and its figures are published strictly as a "
                    "personal, non-commercial comparative evaluation."]


def main() -> int:
    """Write the Romanian audio results page from the result files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = pathlib.Path(args.results)
    summary = json.loads((root / "asr" / "summary.json").read_text())
    lines = [
        "# Romanian audio results", "",
        "> Generated from `../results/audio/` by `../harness/audio/make_report.py`.", "",
        "This report combines a deterministic 100-file FLEURS `ro_ro` pass "
        "with the complete 120-file Echo Romanian diarization set. Read the "
        "[method](audio-method.md) before comparing close figures.", "",
        "## Speech recognition", "",
        *asr_table(summary),
        "", "WER and CER are fractions: `0.100` means ten percent.", "",
        "## Recorded failures", "", *failures(summary),
        "", "## Voice activity detection", "", *vad_section(read(root / "vad.json")),
        "", "## Speaker diarization", "",
        *diarization_section(read(root / "diarization" / "summary.json")),
        "", "## What this establishes", "",
        "The useful result is the trade-off between Romanian transcription or diarization error, loading cost and processing rate on this machine. It is a candidate-selection study, not a claim about all Romanian audio domains.", "",
        "Romanian forced alignment is not included for the reason recorded in [Audio models](audio-models.md).", "",
        "---", "", "[← index](../README.md) · [Audio method](audio-method.md) · [Audio models](audio-models.md)", "",
    ]
    pathlib.Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
