#!/usr/bin/env python3
"""Throughput with long prompts: whole articles, not sentences.

The other tasks in this suite send a sentence or a short passage. Real bulk work
usually sends a document. Prompt length changes how an engine behaves — it is
what fills the key-value cache, and the cache is what limits how many requests
an engine can hold at once — so throughput measured on sentences does not
predict throughput on documents.

This sends whole Wikipedia articles, 2 000 to 5 000 characters each, and asks
for a one-word answer. Input is long, output is short, which is the shape of
classification, routing, extraction and tagging work.

No ground truth is involved. The answer is not marked. The measurement is
requests per second and tokens per second at a given concurrency.

    python3 bench_longform.py <base_url> <label> <concurrency> --articles wiki.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import evalcommon as common

SYSTEM = ("You label documents. Read the article and reply with one word: the "
          "single subject area it belongs to, such as history, biology, music, "
          "sport, politics, geography or technology. One word, nothing else.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base"), parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    parser.add_argument("--articles", default="./eval-data/wikipedia_articles.jsonl")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--languages", help="two-letter codes, comma separated")
    parser.add_argument("--out")
    arguments = parser.parse_args()

    path = pathlib.Path(arguments.articles)
    if not path.exists():
        print(f"no articles at {path} — run fetch_wikipedia.py first", file=sys.stderr)
        return 2

    wanted = ({code.strip() for code in arguments.languages.split(",")}
              if arguments.languages else None)
    articles = []
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        if wanted and row["lang"] not in wanted:
            continue
        articles.append(row)
        if len(articles) >= arguments.limit:
            break
    if not articles:
        print("no articles matched", file=sys.stderr)
        return 2

    lengths = sorted(row["chars"] for row in articles)
    model = common.model_name(arguments.base)
    run = common.Run(arguments.base, model, arguments.concurrency)

    def do(row: dict) -> None:
        run.ask([{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": row["text"]}], max_tokens=16)

    print(f"\n=== {arguments.label} | {model} | {len(articles)} articles "
          f"| concurrency={arguments.concurrency} ===", flush=True)
    run.go(articles, do)

    common.report(arguments.out, {
        "test": "longform_throughput", "set": "Wikipedia articles",
        "label": arguments.label, "model": model,
        "concurrency": arguments.concurrency,
        "articles": len(articles),
        "languages": sorted({row["lang"] for row in articles}),
        "chars_min": lengths[0], "chars_median": lengths[len(lengths) // 2],
        "chars_max": lengths[-1],
        **run.speed(len(articles)),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
