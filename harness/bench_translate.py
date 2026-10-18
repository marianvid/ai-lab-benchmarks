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

import pathlib
import re
import sys

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness import evalcommon as common

try:
    from sacrebleu.metrics import CHRF
except ImportError:                                    # pragma: no cover
    print("this test needs sacrebleu:  pip install sacrebleu", file=sys.stderr)
    raise SystemExit(2) from None

CHRF_PP = CHRF(word_order=2)        # word_order=2 is what makes it chrF++

ENGLISH_MARKERS = re.compile(
    r"\b(the|and|of|to|in|that|with|for|from|this|which|have|been|was|were)\b",
    re.I)
DIGITS = re.compile(r"\d+")


def numbers_in(text: str) -> list[str]:
    """Digits, with group separators removed so 4,475 and 4 475 agree."""
    return DIGITS.findall(re.sub(r"(?<=\d)[ ,.](?=\d{3}\b)", "", text))


def jobs_for(data: pathlib.Path, english: list[str], wanted: list[str],
             limit: int) -> list[dict]:
    """One job per sentence per target language that has a reference file."""
    from harness.get_datasets import LANGUAGES
    jobs = []
    for two in wanted:
        code, name, _script = LANGUAGES[two]
        path = data / f"{code}.txt"
        if not path.exists():
            continue
        reference = path.read_text(encoding="utf-8").splitlines()
        jobs += [{"lang": two, "name": name, "index": index,
                  "source": english[index], "reference": reference[index]}
                 for index in range(min(limit, len(english), len(reference)))]
    return jobs


def translate(run: common.Run, job: dict) -> dict | None:
    """Translate one sentence and score it against the human reference."""
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


def scores(results: list[dict]) -> dict:
    """The chrF++ mean overall and per language, and the two warning counts."""
    by_language: dict[str, list[float]] = {}
    for row in results:
        by_language.setdefault(row["lang"], []).append(row["chrf"])
    return {
        "chrf_mean": round(sum(r["chrf"] for r in results) / len(results), 2)
                     if results else 0.0,
        "chrf_by_language": {lang: round(sum(values) / len(values), 2)
                             for lang, values in sorted(by_language.items())},
        "english_markers_total": sum(r["english_markers"] for r in results),
        "numbers_lost_total": sum(r["numbers_lost"] for r in results),
    }


def main() -> int:
    """Translate FLORES-200 in every direction asked for and score chrF++."""
    parser = common.arguments_parser(__doc__)
    parser.add_argument("--limit", type=int, default=100)
    arguments = parser.parse_args()

    from harness.get_datasets import LANGUAGES
    data = pathlib.Path(arguments.data) / "flores"
    source_file = data / f"{LANGUAGES['en'][0]}.txt"
    if not source_file.exists():
        return common.nothing_found("FLORES data")
    english = source_file.read_text(encoding="utf-8").splitlines()
    wanted = (common.language_list(arguments.languages)
              or [two for two in LANGUAGES if two != "en"])
    jobs = jobs_for(data, english, wanted, arguments.limit)
    if not jobs:
        print("no target languages found", file=sys.stderr)
        return 2

    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)
    common.banner(arguments.label, model, f"{len(jobs)} translations",
                  f"concurrency={arguments.concurrency}")
    results = [row for row in run.go(jobs, lambda job: translate(run, job)) if row]

    common.report(arguments.out, {
        "test": "translation", "set": "FLORES-200",
        "reference": "human translations",
        "label": arguments.label, "model": model,
        "concurrency": arguments.concurrency,
        "translated": len(results), "of": len(jobs),
        **run.speed(len(results)),
        **scores(results),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
