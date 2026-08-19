#!/usr/bin/env python3
"""Topic classification across twenty languages: quality and throughput at once.

The set is SIB-200 — the FLORES sentences, each labelled by people with one of
seven topics. This test asks a yes-or-no question about one topic, and the
default topic is `politics`, which is about one sentence in seven.

**The imbalance is deliberate.** On a set where one answer in seven is yes, a
model that always says no scores 86% accuracy and has understood nothing. F1
catches that; accuracy does not. It is also what separates a model that reads
Lithuanian from one that recognises a few words and guesses.

Both numbers come out of the same pass, because a bulk pipeline cares about
both: how many it got right, and how many it got through per second.

Usage:
    bench_classify.py <base_url> <label> <concurrency> [options]

Options:
    --data DIR        where get_datasets.py put its files (default ./eval-data)
    --topic NAME      which topic is "yes" (default politics)
    --languages LIST  two-letter codes, comma separated (default: all present)
    --batch N         sentences per request (default 5)
    --limit N         at most N sentences per language
    --out FILE        write the result as JSON
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import evalcommon as common

TOPICS = ["science/technology", "travel", "politics", "sports",
          "health", "entertainment", "geography"]

SYSTEM = """You classify sentences by topic. For each sentence, decide whether its topic is: {topic}.

The sentences come from encyclopaedia articles and news, in many languages. Judge the topic of the sentence itself, not whether you recognise the names in it. A name you do not know is still a name.

Answer ONLY with a JSON array, one object per sentence, no markdown fences and no explanation:
[{{"idx": 0, "match": true}}, {{"idx": 1, "match": false}}]"""


def load(data: pathlib.Path, languages: list[str] | None, limit: int | None) -> list[dict]:
    """Every labelled sentence, tagged with the language it is written in."""
    from get_datasets import LANGUAGES
    by_code = {code: two for two, (code, _, _) in LANGUAGES.items()}
    items = []
    for path in sorted((data / "sib200").glob("*.tsv")):
        if path.name.startswith("._"):     # macOS AppleDouble leftovers
            continue
        code = path.stem
        two = by_code.get(code, code)
        if languages and two not in languages:
            continue
        rows = [line.rstrip("\n").split("\t")
                for line in path.open(encoding="utf-8")][1:]
        kept = 0
        for row in rows:
            if len(row) < 3:
                continue
            items.append({"lang": two, "category": row[1], "text": row[2],
                          "id": f"{code}:{row[0]}"})
            kept += 1
            if limit and kept >= limit:
                break
    return items


def parse_answer(text: str) -> dict[int, bool]:
    """Pull the JSON array out of whatever the model wrapped it in."""
    body = text.strip()
    if "```" in body:
        for part in body.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                body = part
                break
    start, end = body.find("["), body.rfind("]")
    if start == -1 or end == -1:
        return {}
    try:
        parsed = json.loads(body[start:end + 1])
    except json.JSONDecodeError:
        return {}
    return {int(entry["idx"]): bool(entry["match"])
            for entry in parsed
            if isinstance(entry, dict) and "idx" in entry and "match" in entry}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base"), parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    parser.add_argument("--data", default="./eval-data")
    parser.add_argument("--topic", default="politics", choices=TOPICS)
    parser.add_argument("--languages")
    parser.add_argument("--batch", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out")
    arguments = parser.parse_args()

    languages = ([code.strip() for code in arguments.languages.split(",")]
                 if arguments.languages else None)
    items = load(pathlib.Path(arguments.data), languages, arguments.limit)
    if not items:
        print("no sentences found — run get_datasets.py first", file=sys.stderr)
        return 2

    batches = [items[i:i + arguments.batch]
               for i in range(0, len(items), arguments.batch)]
    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)
    system = SYSTEM.format(topic=arguments.topic)
    answers: dict[str, bool] = {}

    def do(batch: list[dict]) -> None:
        lines = [json.dumps({"idx": index, "sentence": item["text"]},
                            ensure_ascii=False)
                 for index, item in enumerate(batch)]
        text = run.ask([{"role": "system", "content": system},
                        {"role": "user", "content": "Classify:\n" + "\n".join(lines)}],
                       max_tokens=60 * len(batch) + 200)
        if text is None:
            return
        got = parse_answer(text)
        if not got:
            run.failed += 1
            return
        for index, item in enumerate(batch):
            if index in got:
                answers[item["id"]] = got[index]

    print(f"\n=== {arguments.label} | {model} | topic={arguments.topic} "
          f"| {len(items)} sentences | concurrency={arguments.concurrency} ===",
          flush=True)
    run.go(batches, do)

    overall = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    per_language: dict[str, dict] = {}
    for item in items:
        predicted = answers.get(item["id"])
        if predicted is None:
            continue
        gold = item["category"] == arguments.topic
        key = ("tp" if gold and predicted else "fp" if predicted
               else "fn" if gold else "tn")
        overall[key] += 1
        per_language.setdefault(item["lang"],
                                {"tp": 0, "fp": 0, "tn": 0, "fn": 0})[key] += 1

    common.report(arguments.out, {
        "test": "classification", "set": "SIB-200",
        "label": arguments.label, "model": model, "topic": arguments.topic,
        "concurrency": arguments.concurrency, "batch": arguments.batch,
        "answered": len(answers), "of": len(items),
        **run.speed(len(answers)),
        "quality": common.f1_scores(overall),
        "per_language": {lang: common.f1_scores(counts)
                         for lang, counts in sorted(per_language.items())},
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
