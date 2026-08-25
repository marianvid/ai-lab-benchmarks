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
    return "—" if value is None else f"{value:.{digits}f}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = pathlib.Path(args.results)
    summary = json.loads((root / "asr" / "summary.json").read_text())
    vad_path = root / "vad.json"
    vad = json.loads(vad_path.read_text()) if vad_path.exists() else {}
    diarization_path = root / "diarization" / "summary.json"
    diarization = (json.loads(diarization_path.read_text())
                   if diarization_path.exists() else {})
    lines = [
        "# Romanian audio results", "",
        "> Generated from `results/audio/` by `harness/audio/make_report.py`.", "",
        "This report combines a deterministic 100-file FLEURS `ro_ro` pass "
        "with the complete 120-file Echo Romanian diarization set. Read the "
        "[method](audio-method.md) before comparing close figures.", "",
        "## Speech recognition", "",
        "| Model | Engine | Completed | WER | CER | WER without diacritics | Load | RTF | Audio × real time |",
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
            f"{number(load.get('wall_s'), 1, ' s')} | {number(item.get('real_time_factor'))} | "
            f"{number(item.get('audio_seconds_per_second'), 1, '×')} |")
    lines.extend(["", "WER and CER are fractions: `0.100` means ten percent.", "",
                  "## Recorded failures", ""])
    failures = []
    for key in ORDER:
        item = summary.get(key)
        if not item:
            failures.append(f"- `{key}` has no result file.")
        elif not item.get("load", {}).get("ok"):
            failures.append(f"- **{item.get('model', key)}** did not load: `{item['load'].get('error', 'unknown error')}`")
        elif item.get("status") == "warmup_failed":
            failures.append(f"- **{item.get('model', key)}** loaded, then refused the Romanian warm-up. Its checkpoint lists only English, Spanish and Chinese prompt keys; no accuracy or speed result is claimed.")
        elif item.get("failed"):
            failures.append(f"- **{item.get('model', key)}**: {item['failed']} of {item['requests']} requests failed; see `results/audio/asr/details/{key}.json`.")
    lines.extend(failures or ["No load or transcription request failed."])
    lines.extend(["", "## Voice activity detection", ""])
    vad_summary = vad.get("summary") or {}
    if vad_summary:
        lines.extend([
            f"Silero VAD completed {vad_summary.get('successful')}/{vad_summary.get('requests')} requests in "
            f"{number(vad_summary.get('inference_s'), 2, ' s')}, an RTF of "
            f"{number(vad_summary.get('real_time_factor'), 5)} or "
            f"{number(vad_summary.get('audio_seconds_per_second'), 1, '× real time')}.", "",
            "This is a technical stability and throughput result. FLEURS has no speech-boundary labels, so no VAD quality score is reported.",
        ])
    else:
        lines.append("Silero VAD has no completed result.")
    lines.extend(["", "## Speaker diarization", ""])
    if diarization:
        lines.extend([
            "Echo Synthetic Diarization contains 120 Romanian 60-second files "
            "with reference speaker turns: 60 without overlap and 60 with overlap. "
            "DER uses a 0.25 s collar and scores overlapped speech.", "",
            "| Model | Licence | Completed | DER | No overlap DER | Overlap DER | Load | Audio × real time |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ])
        for key in ("diar-sortformer-4spk-v1", "pyannote-community-1"):
            item = diarization.get(key, {})
            by = item.get("by_condition") or {}
            lines.append(
                f"| {item.get('model', key)} | {item.get('license', '—')} | "
                f"{item.get('successful', 0)}/{item.get('files', 120)} | "
                f"{number((item.get('score') or {}).get('der'))} | "
                f"{number((by.get('no_overlap') or {}).get('der'))} | "
                f"{number((by.get('overlap') or {}).get('der'))} | "
                f"{number((item.get('load') or {}).get('wall_s'), 1, ' s')} | "
                f"{number(item.get('audio_seconds_per_second'), 1, '×')} |")
        lines.extend(["", "Lower DER is better. Sortformer is an NC-licensed "
                      "checkpoint and its figures are published strictly as a "
                      "personal, non-commercial comparative evaluation."])
    else:
        lines.append("No diarization run has been recorded.")
    lines.extend(["", "## What this establishes", "",
                  "The useful result is the trade-off between Romanian transcription or diarization error, loading cost and processing rate on this machine. It is a candidate-selection study, not a claim about all Romanian audio domains.", "",
                  "Romanian forced alignment is not included for the reason recorded in [Audio models](audio-models.md).", "",
                  "---", "", "[← index](../README.md) · [Audio method](audio-method.md) · [Audio models](audio-models.md)", ""])
    pathlib.Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
