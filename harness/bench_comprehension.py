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

import json
import pathlib
import re
import sys

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness import evalcommon as common

LETTERS = "ABCD"

SYSTEM = """You answer multiple-choice reading questions.

You are given a passage, a question about it, and four answers labelled A, B, C and D. Exactly one is correct. The answer is always contained in the passage — do not use outside knowledge, and do not object that the passage is incomplete.

Reply with one letter and nothing else: A, B, C or D."""

# A model that has been asked for one letter will still sometimes write a
# sentence around it. Take the first letter that stands alone.
LETTER_RE = re.compile(r"\b([ABCD])\b")


def load(data: pathlib.Path, languages: list[str] | None, limit: int) -> list[dict]:
    """Belebele questions for the languages asked for, at most `limit` per language."""
    from harness.get_datasets import LANGUAGES
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


class Reading:
    """One pass over the questions: the answers, and what came back instead."""

    def __init__(self, run: common.Run) -> None:
        self.run = run
        self.answers: dict[str, str] = {}
        # What came back when no letter did. A count alone says a model failed
        # without saying how, and the answer to "which ones?" was "not recorded".
        self.misses: list[dict] = []

    def miss(self, item: dict, reason: str, returned: str | None) -> None:
        """Record a question that produced no letter."""
        self.misses.append({"id": item["id"], "lang": item["lang"],
                            "reason": reason, "returned": returned})

    def ask(self, item: dict) -> None:
        """Ask one question and record the letter, or why there was none."""
        options = "\n".join(f"{LETTERS[n]}. {text}"
                            for n, text in enumerate(item["options"]))
        user = (f"Passage:\n{item['passage']}\n\n"
                f"Question: {item['question']}\n\n{options}\n\nAnswer:")
        text = self.run.ask([{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": user}], max_tokens=8)
        if text is None:
            self.miss(item, "request failed", None)
            return
        found = LETTER_RE.search(text.upper())
        if found:
            self.answers[item["id"]] = found.group(1)
        else:
            self.run.failed += 1
            self.miss(item, "no letter in the answer", text[:200])

    def per_language(self, items: list[dict]) -> dict[str, dict]:
        """Accuracy per language, over the questions that were answered."""
        marks: dict[str, list[int]] = {}
        for item in items:
            answer = self.answers.get(item["id"])
            if answer is None:
                continue
            marks.setdefault(item["lang"], []).append(
                1 if answer == item["correct"] else 0)
        return {lang: {"n": len(got), "accuracy": round(sum(got) / len(got), 4)}
                for lang, got in sorted(marks.items())}


def main() -> int:
    """Answer every Belebele question and report accuracy and speed."""
    parser = common.arguments_parser(__doc__)
    parser.add_argument("--limit", type=int, default=200)
    arguments = parser.parse_args()

    items = load(pathlib.Path(arguments.data), common.language_list(arguments.languages),
                 arguments.limit)
    if not items:
        return common.nothing_found("questions")

    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)
    reading = Reading(run)
    common.banner(arguments.label, model, f"{len(items)} questions",
                  f"concurrency={arguments.concurrency}")
    run.go(items, reading.ask)

    answers = reading.answers
    right = sum(1 for item in items if answers.get(item["id"]) == item["correct"])
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
        "misses": sorted(reading.misses, key=lambda m: (m["lang"], m["id"])),
        "per_language": reading.per_language(items),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
