#!/usr/bin/env python3
"""Score generated TTS audio through one deployed AI-Lab ASR evaluator."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from harness.shared.lab import MANAGER_HELP, api, manager_url, multipart
from harness.shared.textmetrics import error_counts

LANGUAGE_ALIASES = {"en": {"en", "English"}, "ro": {"ro", "Romanian"}}
# Cases are also scored per speaker and per gender when the case says which.
GROUP_KEYS = ("gender", "speaker")


def ratio(part: int, whole: int) -> float | None:
    """part / whole, or None when there was nothing to count."""
    return part / whole if whole else None


def summed(left: list[int], right: tuple[int, ...] | list[int]) -> list[int]:
    """Two lists of counts, added place by place."""
    return [a + b for a, b in zip(left, right, strict=True)]


class Scores:
    """Error counts of one generated set: overall, per mode, with and without diacritics."""

    def __init__(self) -> None:
        self.overall = [0, 0, 0, 0]
        self.overall_ascii = [0, 0, 0, 0]
        self.by_mode: dict[str, list[int]] = {}
        self.by_mode_ascii: dict[str, list[int]] = {}

    def add(self, mode: str, reference: str, hypothesis: str) -> tuple[int, int, int, int]:
        """Count one case; returns its plain counts."""
        plain = error_counts(reference, hypothesis)
        stripped = error_counts(reference, hypothesis, True)
        self.overall = summed(self.overall, plain)
        self.overall_ascii = summed(self.overall_ascii, stripped)
        self.by_mode[mode] = summed(self.by_mode.get(mode, [0, 0, 0, 0]), plain)
        self.by_mode_ascii[mode] = summed(self.by_mode_ascii.get(mode, [0, 0, 0, 0]), stripped)
        return plain

    def summary(self, records: list[dict]) -> dict:
        """WER and CER overall and per mode, then per group, then every case."""
        return {
            "wer": ratio(self.overall[0], self.overall[1]),
            "cer": ratio(self.overall[2], self.overall[3]),
            "wer_without_diacritics": ratio(self.overall_ascii[0], self.overall_ascii[1]),
            "completed": len(records),
            "by_mode": {mode: {"wer": ratio(values[0], values[1]),
                               "cer": ratio(values[2], values[3]),
                               "wer_without_diacritics": ratio(self.by_mode_ascii[mode][0],
                                                               self.by_mode_ascii[mode][1])}
                        for mode, values in self.by_mode.items()},
            **groups(records), "cases": records,
        }


def group(records: list[dict], key: str, value) -> dict:
    """WER and CER over the scored cases whose `key` is `value`."""
    rows = [record for record in records
            if record.get(key) == value and "word_errors" in record]
    return {
        "wer": ratio(sum(row["word_errors"] for row in rows),
                     sum(row["reference_words"] for row in rows)),
        "cer": ratio(sum(row["character_errors"] for row in rows),
                     sum(row["reference_characters"] for row in rows)),
        "completed": len(rows),
    }


def groups(records: list[dict]) -> dict:
    """WER and CER per gender and per speaker, for the cases that say which."""
    found: dict = {}
    for key in GROUP_KEYS:
        values = sorted({record[key] for record in records if key in record})
        if values:
            found[f"by_{key}"] = {value: group(records, key, value) for value in values}
    return found


class Evaluator:
    """The ASR model scoring the generated speech, through the manager."""

    def __init__(self, manager: str, instance: str, language: str) -> None:
        self.manager = manager
        self.instance = instance
        self.language = language

    def transcribe(self, audio: Path) -> str:
        """One generated file's text, as the evaluator hears it."""
        response = multipart(self.manager + "/v1/audio/transcriptions",
                             {"model": self.instance, "language": self.language},
                             ("file", audio.name, audio.read_bytes()))
        return str(response.get("text", ""))

    def score_set(self, root: Path) -> dict:
        """Every generated case of one model in this language, scored."""
        raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
        scores = Scores()
        records = []
        for case in raw["cases"]:
            if not case.get("ok") or case["language"] not in LANGUAGE_ALIASES[self.language]:
                continue
            record = self.score_case(root, case, scores)
            records.append(record)
            print(json.dumps({"model": root.name, **record}, ensure_ascii=False), flush=True)
        return scores.summary(records)

    def score_case(self, root: Path, case: dict, scores: Scores) -> dict:
        """One case: transcribed and counted, or the error that stopped it."""
        started = time.perf_counter()
        try:
            hypothesis = self.transcribe(root / "audio" / f"{case['id']}.wav")
        except Exception as error:
            return {"id": case["id"], "error": f"{type(error).__name__}: {error}"}
        reference = case.get("expected_text", case["text"])
        mode = case.get("mode", "default")
        counted = scores.add(mode, reference, hypothesis)
        record = {"id": case["id"], "reference": reference, "hypothesis": hypothesis,
                  "seconds": round(time.perf_counter() - started, 6), "mode": mode,
                  "word_errors": counted[0], "reference_words": counted[1],
                  "character_errors": counted[2], "reference_characters": counted[3]}
        record.update({key: case[key] for key in GROUP_KEYS if key in case})
        return record


def main() -> int:
    """Load the evaluator, score every result set given, unload, write one JSON file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", help=MANAGER_HELP)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--language", required=True, choices=("ro", "en"))
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", help="Optional explicit destination JSON path")
    args = parser.parse_args()
    manager = manager_url(args.manager)
    evaluator = Evaluator(manager, args.evaluator, args.language)
    loaded = api(manager, f"/api/instances/{args.evaluator}/load", "POST", body={})
    output = {"schema_version": 1, "evaluator": args.evaluator,
              "language": args.language, "load": loaded, "models": {}}
    try:
        for name in args.result:
            root = Path(name).resolve()
            output["models"][root.name] = evaluator.score_set(root)
        print(json.dumps({name: {k: v for k, v in value.items() if k != "cases"}
                          for name, value in output["models"].items()}, indent=2), flush=True)
    finally:
        output["unload"] = api(manager, f"/api/instances/{args.evaluator}/unload", "POST",
                               300, body={})
    destination = (Path(args.out).resolve() if args.out else
                   Path(args.result[0]).resolve().parent /
                   f"asr-{args.evaluator}-{args.language}.json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
