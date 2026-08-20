#!/usr/bin/env python3
"""Reading comprehension across twenty languages, marked mechanically.

The set is Belebele: a passage, a question about it, and four answers of which
exactly one is right — written and checked by people, over the same FLORES
passages the other tests use.

**This is the test a model cannot bluff.** Classification can be half-guessed
from a keyword. A translation can be scored well while being subtly wrong. Here
the model has to have understood a passage it may never have seen in a language
it may barely know, and the marking is one letter: A, B, C or D.

It is also the closest test here to real prompt lengths, because a passage is
not a sentence.

Usage:
    bench_comprehension.py <base_url> <label> <concurrency> [options]

Options:
    --data DIR        where get_datasets.py put its files (default ./eval-data)
    --languages LIST  two-letter codes, comma separated (default: all present)
    --limit N         at most N questions per language (default 200)
    --out FILE        write the result as JSON
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import evalcommon as common

LETTERS = "ABCD"

SYSTEM = """You answer multiple-choice reading questions.

You are given a passage, a question about it, and four answers labelled A, B, C and D. Exactly one is correct. The answer is always contained in the passage — do not use outside knowledge, and do not object that the passage is incomplete.

Reply with one letter and nothing else: A, B, C or D."""

# A model that has been asked for one letter will still sometimes write a
# sentence around it. Take the first letter that stands alone.
LETTER_RE = re.compile(r"\b([ABCD])\b")


def load(data: pathlib.Path, languages: list[str] | None, limit: int) -> list[dict]:
    from get_datasets import LANGUAGES
    by_code = {code: two for two, (code, _, _) in LANGUAGES.items()}
    items = []
    for path in sorted((data / "belebele").glob("*.jsonl")):
        if path.name.startswith("._"):     # macOS AppleDouble leftovers
            continue
        two = by_code.get(path.stem, path.stem)
        if languages and two not in languages:
            continue
        # Always the first N, never a random N: every model must be asked the
        # same questions or the scores cannot be put in one table.
        for index, line in enumerate(path.open(encoding="utf-8")):
            if index >= limit:
                break
            row = json.loads(line)
            items.append({
                "lang": two, "id": f"{path.stem}:{index}",
                "passage": row["flores_passage"], "question": row["question"],
                "options": [row[f"mc_answer{n}"] for n in range(1, 5)],
                "correct": LETTERS[int(row["correct_answer_num"]) - 1],
            })
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base"), parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    parser.add_argument("--data", default="./eval-data")
    parser.add_argument("--languages")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--out")
    arguments = parser.parse_args()

    languages = ([code.strip() for code in arguments.languages.split(",")]
                 if arguments.languages else None)
    items = load(pathlib.Path(arguments.data), languages, arguments.limit)
    if not items:
        print("no questions found — run get_datasets.py first", file=sys.stderr)
        return 2

    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)
    answers: dict[str, str] = {}
    # What came back when no letter did. A count alone says a model failed
    # without saying how, and the answer to "which ones?" was "not recorded".
    misses: list[dict] = []

    def do(item: dict) -> None:
        options = "\n".join(f"{LETTERS[n]}. {text}"
                            for n, text in enumerate(item["options"]))
        user = (f"Passage:\n{item['passage']}\n\n"
                f"Question: {item['question']}\n\n{options}\n\nAnswer:")
        text = run.ask([{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": user}], max_tokens=8)
        if text is None:
            misses.append({"id": item["id"], "lang": item["lang"],
                           "reason": "request failed", "returned": None})
            return
        found = LETTER_RE.search(text.upper())
        if found:
            answers[item["id"]] = found.group(1)
        else:
            run.failed += 1
            misses.append({"id": item["id"], "lang": item["lang"],
                           "reason": "no letter in the answer",
                           "returned": text[:200]})

    print(f"\n=== {arguments.label} | {model} | {len(items)} questions "
          f"| concurrency={arguments.concurrency} ===", flush=True)
    run.go(items, do)

    right = sum(1 for item in items if answers.get(item["id"]) == item["correct"])
    per_language: dict[str, list[int]] = {}
    for item in items:
        answer = answers.get(item["id"])
        if answer is None:
            continue
        per_language.setdefault(item["lang"], []).append(
            1 if answer == item["correct"] else 0)

    # A four-way choice scores 25% by guessing. Anything near that means the
    # model did not read the passage, whatever else the number looks like.
    common.report(arguments.out, {
        "test": "comprehension", "set": "Belebele",
        "label": arguments.label, "model": model,
        "concurrency": arguments.concurrency,
        "answered": len(answers), "of": len(items),
        "chance_level": 0.25,
        **run.speed(len(answers)),
        "accuracy": round(right / len(items), 4) if items else 0.0,
        # Every question that produced no letter, with what came back instead.
        "misses": sorted(misses, key=lambda m: (m["lang"], m["id"])),
        "per_language": {lang: {"n": len(marks),
                                "accuracy": round(sum(marks) / len(marks), 4)}
                         for lang, marks in sorted(per_language.items())},
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
