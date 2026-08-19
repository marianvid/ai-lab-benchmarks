#!/usr/bin/env python3
"""Translation out of English into nineteen languages, scored against people.

The set is FLORES-200: the same sentences translated by professional
translators into two hundred languages. That matters more than it sounds. The
previous version of this test scored against reference translations produced by
a model, which meant a good chrF++ figure proved agreement with another
machine. Here it means agreement with a person.

Scoring is chrF++ from `sacrebleu`, the standard implementation. Mechanical, no
judge model, no family bias, reproducible by anyone with the same two files.

Two cheap checks run alongside, because a score can hide a disaster:

  - **English left in place.** Counts common English function words in the
    output. Weak on its own — most hits are organisation names correctly kept —
    so use it to find candidates to read, not as a score.
  - **Numbers lost.** Compares the digits in source and output. Digit group
    separators are stripped first, because 4,475 legitimately becomes 4 475.

Usage:
    bench_translate.py <base_url> <label> <concurrency> [options]

Options:
    --data DIR        where get_datasets.py put its files (default ./eval-data)
    --languages LIST  target codes, comma separated (default: all but English)
    --limit N         at most N sentences per language (default 100)
    --out FILE        write the result as JSON
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

import evalcommon as common

try:
    from sacrebleu.metrics import CHRF
except ImportError:                                    # pragma: no cover
    print("this test needs sacrebleu:  pip install sacrebleu", file=sys.stderr)
    raise SystemExit(2)

CHRF_PP = CHRF(word_order=2)        # word_order=2 is what makes it chrF++

ENGLISH_MARKERS = re.compile(
    r"\b(the|and|of|to|in|that|with|for|from|this|which|have|been|was|were)\b",
    re.I)
DIGITS = re.compile(r"\d+")


def numbers_in(text: str) -> list[str]:
    """Digits, with group separators removed so 4,475 and 4 475 agree."""
    return DIGITS.findall(re.sub(r"(?<=\d)[ ,.](?=\d{3}\b)", "", text))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base"), parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    parser.add_argument("--data", default="./eval-data")
    parser.add_argument("--languages")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out")
    arguments = parser.parse_args()

    from get_datasets import LANGUAGES
    data = pathlib.Path(arguments.data) / "flores"
    source_file = data / f"{LANGUAGES['en'][0]}.txt"
    if not source_file.exists():
        print("no FLORES data — run get_datasets.py first", file=sys.stderr)
        return 2
    english = source_file.read_text(encoding="utf-8").splitlines()

    wanted = ([code.strip() for code in arguments.languages.split(",")]
              if arguments.languages
              else [two for two in LANGUAGES if two != "en"])

    jobs = []
    for two in wanted:
        code, name, _script = LANGUAGES[two]
        path = data / f"{code}.txt"
        if not path.exists():
            continue
        reference = path.read_text(encoding="utf-8").splitlines()
        for index in range(min(arguments.limit, len(english), len(reference))):
            jobs.append({"lang": two, "name": name, "index": index,
                         "source": english[index], "reference": reference[index]})
    if not jobs:
        print("no target languages found", file=sys.stderr)
        return 2

    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)

    def do(job: dict) -> dict | None:
        system = (f"You are a professional translator. Translate the user's text "
                  f"from English into {job['name']}. Reply with the translation "
                  f"only: no notes, no explanation, no quotation marks around it.")
        text = run.ask([{"role": "system", "content": system},
                        {"role": "user", "content": job["source"]}],
                       max_tokens=1024)
        if text is None:
            return None
        score = CHRF_PP.sentence_score(text, [job["reference"]]).score
        source_numbers, output_numbers = numbers_in(job["source"]), numbers_in(text)
        return {"lang": job["lang"], "index": job["index"],
                "chrf": round(score, 2),
                "english_markers": len(ENGLISH_MARKERS.findall(text)),
                "numbers_lost": max(0, len(source_numbers) - len(output_numbers))}

    print(f"\n=== {arguments.label} | {model} | {len(jobs)} translations "
          f"| concurrency={arguments.concurrency} ===", flush=True)
    results = [row for row in run.go(jobs, do) if row]

    by_language: dict[str, list[float]] = {}
    for row in results:
        by_language.setdefault(row["lang"], []).append(row["chrf"])

    common.report(arguments.out, {
        "test": "translation", "set": "FLORES-200",
        "reference": "human translations",
        "label": arguments.label, "model": model,
        "concurrency": arguments.concurrency,
        "translated": len(results), "of": len(jobs),
        **run.speed(len(results)),
        "chrf_mean": round(sum(r["chrf"] for r in results) / len(results), 2)
                     if results else 0.0,
        "chrf_by_language": {lang: round(sum(scores) / len(scores), 2)
                             for lang, scores in sorted(by_language.items())},
        "english_markers_total": sum(r["english_markers"] for r in results),
        "numbers_lost_total": sum(r["numbers_lost"] for r in results),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
