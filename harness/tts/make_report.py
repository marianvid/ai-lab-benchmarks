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
    """The value at `fraction` of the sorted values, interpolated linearly."""
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


# The interval: 95% of 10 000 resamples, from a fixed seed so it repeats.
RESAMPLES = 10000
SEED = 20260915
LOW, HIGH = 0.025, 0.975


def ratio(rows: list[dict], top: str, bottom: str) -> float:
    """The sum of one field over the sum of another."""
    return sum(row[top] for row in rows) / sum(row[bottom] for row in rows)


def statistic(rows: list[dict], metric: str) -> float:
    """The metric over a set of rows: WER and RTF are ratios of sums, the rest means."""
    if metric == "wer":
        return ratio(rows, "word_errors", "reference_words")
    if metric == "rtf":
        return ratio(rows, "seconds", "audio_duration_s")
    return sum(row[metric] for row in rows) / len(rows)


def bootstrap(rows: list[dict], metric: str, seed: int = SEED) -> list[float] | None:
    """A 95% interval of the metric's mean, resampling whole speakers."""
    by_speaker: dict[str, list[dict]] = {}
    for row in rows:
        by_speaker.setdefault(row["speaker"], []).append(row)
    speakers = sorted(by_speaker)
    if not speakers:
        return None
    rng, estimates = random.Random(seed), []
    for _ in range(RESAMPLES):
        sampled = [rng.choice(speakers) for _ in speakers]
        estimates.append(statistic(
            [row for speaker in sampled for row in by_speaker[speaker]], metric))
    return [round(percentile(estimates, LOW), 6),
            round(percentile(estimates, HIGH), 6)]


class Scores:
    """The four score files and the manifest, read once."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.asr = json.loads((root / "libritts-asr-whisper-large-v3-en.json").read_text())
        self.mos = json.loads((root / "libritts-utmos22-strong.json").read_text())
        self.similarity = json.loads((root / "libritts-speaker-similarity.json").read_text())
        manifest = json.loads((root / "libritts-en100-manifest.json").read_text())
        self.targets = {row["id"]: row["target_duration_s"] for row in manifest["cases"]}

    def by_gender(self, model_id: str) -> dict:
        """WER, UTMOS and voice similarity for the female and the male speakers."""
        asr = self.asr["models"][model_id].get("by_gender", {})
        mos = self.mos["models"][model_id].get("by_gender", {})
        similar = self.similarity["models"][model_id]["generated_to_target"]["by_gender"]
        return {gender: {"wer": asr.get(gender, {}).get("wer"),
                         "utmos": mos.get(gender),
                         "speaker_similarity_to_target": similar.get(gender)}
                for gender in ("F", "M")}

    def quality(self, model_id: str) -> dict:
        """The evaluator scores for one model, with their intervals."""
        asr = self.asr["models"][model_id]
        mos = self.mos["models"][model_id]
        similar = self.similarity["models"][model_id]
        return {
            "wer": asr["wer"],
            "wer_ci95": bootstrap(asr["cases"], "wer"),
            "cer": asr["cer"],
            "utmos": mos["mean"],
            "utmos_ci95": bootstrap(mos["cases"], "mos"),
            "speaker_similarity_to_target": similar["generated_to_target"]["mean"],
            "speaker_similarity_ci95": bootstrap(similar["cases"], "generated_to_target"),
            "speaker_similarity_to_enrollment": similar["generated_to_reference"]["mean"],
        }

    def cost(self, raw: dict, cases: list[dict]) -> dict:
        """Speed, length against the human recording, and memory."""
        timed_cases = [{**row, "target_duration_s": self.targets[row["id"]]}
                       for row in cases]
        rtf = (ratio(cases, "seconds", "audio_duration_s")
               if cases and "seconds" in cases[0] else None)
        return {
            "rtf": round(rtf, 6) if rtf is not None else None,
            "rtf_ci95": bootstrap(cases, "rtf") if rtf is not None else None,
            "duration_ratio": (round(ratio(timed_cases, "audio_duration_s",
                                           "target_duration_s"), 6)
                               if timed_cases else None),
            "peak_vram_bytes": max(filter(None, (
                raw.get("peak_vram_bytes"), raw.get("max_gpu_process_memory_bytes"))),
                default=None),
        }

    def model(self, model_id: str, label: str) -> dict:
        """Everything recorded about one model."""
        raw = json.loads((self.root / model_id / "raw.json").read_text())
        cases = [row for row in raw["cases"] if row.get("ok")]
        return {"label": label, "completed": len(cases),
                "failures": len(raw["cases"]) - len(cases),
                **self.quality(model_id), **self.cost(raw, cases),
                "by_gender": self.by_gender(model_id)}


def value(number, digits=3):
    """A number to `digits` places, or a dash."""
    return "—" if number is None else f"{number:.{digits}f}"


def interval(pair):
    """An interval as low–high, or a dash."""
    return "—" if pair is None else f"{pair[0]:.3f}–{pair[1]:.3f}"


def score_row(model: dict) -> str:
    """One model's line in the main table."""
    memory = model["peak_vram_bytes"]
    return "| {label} | {completed}/100 | {wer} | {mos} | {sim} | {duration} | {rtf} | {memory} |".format(
        label=model["label"], completed=model["completed"],
        wer=value(model["wer"]), mos=value(model["utmos"]),
        sim=value(model["speaker_similarity_to_target"]), rtf=value(model["rtf"]),
        duration=value(model["duration_ratio"]),
        memory="—" if not memory else f"{memory / 1e9:.1f} GB")


def interval_row(model: dict) -> str:
    """One model's line in the confidence-interval table."""
    return (f"| {model['label']} | {interval(model['wer_ci95'])} | "
            f"{interval(model['utmos_ci95'])} | {interval(model['speaker_similarity_ci95'])} | "
            f"{interval(model['rtf_ci95'])} |")


def page(models: list[dict]) -> list[str]:
    """The results page."""
    return [
        "# Text-to-speech results", "",
        "> Generated by `harness/tts/make_report.py` from the committed raw measurements.", "",
        "The verdicts on this page are automatic. They describe the measured test set,",
        "not every voice, script or production use.", "",
        "The serious English pass contains 100 held-out sentences from ten LibriTTS `test-clean` speakers (five female, five male). Intervals are 95% speaker-bootstrap intervals over 10,000 deterministic resamples.", "",
        "| Model | Completed | WER ↓ | UTMOS ↑ | Voice similarity to held-out target ↑ | Duration / human | RTF ↓ | Peak GPU memory |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *(score_row(model) for model in models),
        "", "WER and RTF are lower-is-better. UTMOS and cosine voice similarity are higher-is-better. The human row calibrates the automatic evaluators; it is not a synthetic model.", "",
        "## Confidence intervals", "",
        "| Model | WER 95% CI | UTMOS 95% CI | Voice similarity 95% CI | RTF 95% CI |",
        "|---|---:|---:|---:|---:|",
        *(interval_row(model) for model in models),
        "", "## What the scores do not measure", "",
        "These measurements cover intelligibility, predicted naturalness, speaker retention,",
        "stability and machine cost. They do not score acting, pacing, emphasis or fit with a",
        "particular programme.", "",
        "---", "", "[← index](../README.md) · [TTS method](tts-method.md) · [TTS models](tts-models.md) · [Listening samples](https://marianvid.github.io/ai-lab-benchmarks/docs/tts-listening.html)", "",
    ]


def main() -> int:
    """Combine every score into the TTS results JSON and page."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()
    scores = Scores(Path(args.results).resolve())
    output: dict = {"schema_version": 1, "benchmark": "libritts-test-clean-en100-v1",
                    "confidence_intervals": f"95% speaker bootstrap, {RESAMPLES} resamples, seed {SEED}",
                    "models": {model_id: scores.model(model_id, label)
                               for model_id, label in LABELS.items()}}
    Path(args.out_json).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    Path(args.out_md).write_text("\n".join(page(list(output["models"].values()))),
                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
