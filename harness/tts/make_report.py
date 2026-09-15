#!/usr/bin/env python3
"""Build the publishable English TTS table with speaker-bootstrap intervals."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


LABELS = {
    "libritts-ground-truth-en100-v1": "Human LibriTTS target",
    "libritts-omnivoice-en100-v1": "OmniVoice 0.6B",
    "libritts-qwen-en100-v1": "Qwen3-TTS 0.6B Base",
    "libritts-firered-base-en100-v1": "FireRedTTS3 Base",
    "libritts-firered-instruct-en100-v1": "FireRedTTS3 Instruct clone",
    "libritts-fish-en100-v1": "Fish Audio S2 Pro",
}


def percentile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def bootstrap(rows: list[dict], metric: str, seed: int = 20260915) -> list[float] | None:
    by_speaker = {}
    for row in rows:
        by_speaker.setdefault(row["speaker"], []).append(row)
    speakers = sorted(by_speaker)
    if not speakers:
        return None
    rng, estimates = random.Random(seed), []
    for _ in range(10000):
        sampled = [rng.choice(speakers) for _ in speakers]
        picked = [row for speaker in sampled for row in by_speaker[speaker]]
        if metric == "wer":
            value = sum(row["word_errors"] for row in picked) / sum(
                row["reference_words"] for row in picked)
        elif metric == "rtf":
            value = sum(row["seconds"] for row in picked) / sum(
                row["audio_duration_s"] for row in picked)
        else:
            value = sum(row[metric] for row in picked) / len(picked)
        estimates.append(value)
    return [round(percentile(estimates, 0.025), 6),
            round(percentile(estimates, 0.975), 6)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()
    root = Path(args.results).resolve()
    asr = json.loads((root / "libritts-asr-whisper-large-v3-en.json").read_text())
    mos = json.loads((root / "libritts-utmos22-strong.json").read_text())
    similarity = json.loads((root / "libritts-speaker-similarity.json").read_text())
    manifest = json.loads((root / "libritts-en100-manifest.json").read_text())
    targets = {row["id"]: row["target_duration_s"] for row in manifest["cases"]}
    output = {"schema_version": 1, "benchmark": "libritts-test-clean-en100-v1",
              "confidence_intervals": "95% speaker bootstrap, 10000 resamples, seed 20260915",
              "models": {}}
    for model_id, label in LABELS.items():
        raw = json.loads((root / model_id / "raw.json").read_text())
        cases = [row for row in raw["cases"] if row.get("ok")]
        timed_cases = [{**row, "target_duration_s": targets[row["id"]]} for row in cases]
        asr_rows = asr["models"][model_id]["cases"]
        mos_rows = mos["models"][model_id]["cases"]
        sim_rows = similarity["models"][model_id]["cases"]
        rtf = (sum(row["seconds"] for row in cases) /
               sum(row["audio_duration_s"] for row in cases)) if cases and "seconds" in cases[0] else None
        model = {
            "label": label, "completed": len(cases),
            "failures": len(raw["cases"]) - len(cases),
            "wer": asr["models"][model_id]["wer"],
            "wer_ci95": bootstrap(asr_rows, "wer"),
            "cer": asr["models"][model_id]["cer"],
            "utmos": mos["models"][model_id]["mean"],
            "utmos_ci95": bootstrap(mos_rows, "mos"),
            "speaker_similarity_to_target": similarity["models"][model_id][
                "generated_to_target"]["mean"],
            "speaker_similarity_ci95": bootstrap(sim_rows, "generated_to_target"),
            "speaker_similarity_to_enrollment": similarity["models"][model_id][
                "generated_to_reference"]["mean"],
            "rtf": round(rtf, 6) if rtf is not None else None,
            "rtf_ci95": bootstrap(cases, "rtf") if rtf is not None else None,
            "duration_ratio": (round(sum(row["audio_duration_s"] for row in timed_cases) /
                                     sum(row["target_duration_s"] for row in timed_cases), 6)
                               if timed_cases else None),
            "peak_vram_bytes": max(filter(None, (
                raw.get("peak_vram_bytes"), raw.get("max_gpu_process_memory_bytes"))),
                default=None),
            "by_gender": {
                gender: {
                    "wer": asr["models"][model_id].get("by_gender", {}).get(gender, {}).get("wer"),
                    "utmos": mos["models"][model_id].get("by_gender", {}).get(gender),
                    "speaker_similarity_to_target": similarity["models"][model_id][
                        "generated_to_target"]["by_gender"].get(gender),
                } for gender in ("F", "M")
            },
        }
        output["models"][model_id] = model
    Path(args.out_json).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    def value(number, digits=3):
        return "—" if number is None else f"{number:.{digits}f}"

    lines = [
        "# Text-to-speech results", "",
        "> Generated by `harness/tts/make_report.py` from the committed raw measurements.", "",
        "The verdicts on this page are automatic. They describe the measured test set,",
        "not every voice, script or production use.", "",
        "The serious English pass contains 100 held-out sentences from ten LibriTTS `test-clean` speakers (five female, five male). Intervals are 95% speaker-bootstrap intervals over 10,000 deterministic resamples.", "",
        "| Model | Completed | WER ↓ | UTMOS ↑ | Voice similarity to held-out target ↑ | Duration / human | RTF ↓ | Peak GPU memory |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in output["models"].values():
        memory = model["peak_vram_bytes"]
        lines.append("| {label} | {completed}/100 | {wer} | {mos} | {sim} | {duration} | {rtf} | {memory} |".format(
            label=model["label"], completed=model["completed"],
            wer=value(model["wer"]), mos=value(model["utmos"]),
            sim=value(model["speaker_similarity_to_target"]), rtf=value(model["rtf"]),
            duration=value(model["duration_ratio"]),
            memory="—" if not memory else f"{memory / 1e9:.1f} GB"))
    lines.extend([
        "", "WER and RTF are lower-is-better. UTMOS and cosine voice similarity are higher-is-better. The human row calibrates the automatic evaluators; it is not a synthetic model.", "",
        "## Confidence intervals", "",
        "| Model | WER 95% CI | UTMOS 95% CI | Voice similarity 95% CI | RTF 95% CI |",
        "|---|---:|---:|---:|---:|",
    ])
    for model in output["models"].values():
        def interval(pair):
            return "—" if pair is None else f"{pair[0]:.3f}–{pair[1]:.3f}"
        lines.append(f"| {model['label']} | {interval(model['wer_ci95'])} | "
                     f"{interval(model['utmos_ci95'])} | {interval(model['speaker_similarity_ci95'])} | "
                     f"{interval(model['rtf_ci95'])} |")
    lines.extend([
        "", "## What the scores do not measure", "",
        "These measurements cover intelligibility, predicted naturalness, speaker retention,",
        "stability and machine cost. They do not score acting, pacing, emphasis or fit with a",
        "particular programme.", "",
        "---", "", "[← index](../README.md) · [TTS method](tts-method.md) · [TTS models](tts-models.md) · [Listening samples](https://marianvid.github.io/ai-lab-benchmarks/docs/tts-listening.html)", "",
    ])
    Path(args.out_md).write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
