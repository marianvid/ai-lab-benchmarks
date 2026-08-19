#!/usr/bin/env python3
"""How many characters a token buys, in each writing system.

The same sentence is not the same number of tokens in Latin, Cyrillic, Han and
Devanagari — and tokens are the unit of everything that costs: how much context
fits, how long reading takes, how much a hosted model charges. A study that
covers twenty languages in ten scripts should say what that costs.

It needs no GPU and no engine: it only asks each model's tokenizer to count.
Seconds, not hours.

    python3 tokratio.py --data ./eval-data --models /models/nvfp4/gemma-4-26b-a4b

Reads the FLORES sentences, which are the same text in every language, so the
comparison is exact rather than approximate: differences in the count are
differences in the script and the tokenizer, not in what was said.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

try:
    from transformers import AutoTokenizer
except ImportError:                                     # pragma: no cover
    print("this script needs transformers:  pip install transformers",
          file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="./eval-data")
    parser.add_argument("--models", nargs="+", required=True,
                        help="paths to model directories with a tokenizer")
    parser.add_argument("--limit", type=int, default=200,
                        help="sentences per language")
    parser.add_argument("--out")
    arguments = parser.parse_args()

    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from get_datasets import LANGUAGES

    flores = pathlib.Path(arguments.data) / "flores"
    text: dict[str, list[str]] = {}
    for two, (code, _name, _script) in LANGUAGES.items():
        path = flores / f"{code}.txt"
        if path.exists():
            text[two] = path.read_text(encoding="utf-8").splitlines()[:arguments.limit]
    if not text:
        print("no FLORES data — run get_datasets.py first", file=sys.stderr)
        return 2

    report: dict[str, dict] = {}
    for model in arguments.models:
        name = pathlib.Path(model).name
        try:
            tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        except Exception as error:
            print(f"{name}: {repr(error)[:100]}", file=sys.stderr)
            continue

        print(f"\n### {name}")
        print(f"{'lang':<6}{'script':<12}{'chars':>9}{'tokens':>9}{'chars/token':>13}")
        rows = {}
        for two in sorted(text, key=lambda k: LANGUAGES[k][2]):
            script = LANGUAGES[two][2]
            characters = sum(len(line) for line in text[two])
            tokens = sum(len(tokenizer.encode(line, add_special_tokens=False))
                         for line in text[two])
            ratio = characters / tokens if tokens else 0.0
            rows[two] = {"script": script, "chars": characters,
                         "tokens": tokens, "chars_per_token": round(ratio, 2)}
            print(f"{two:<6}{script:<12}{characters:>9}{tokens:>9}{ratio:>13.2f}")

        # English is the reference: everything else is quoted as a multiple of
        # what the same content costs in English, which is the number that
        # decides whether a context window is enough.
        english = rows.get("en", {}).get("tokens")
        if english:
            print(f"\n  tokens relative to English, for the same sentences:")
            for two, row in sorted(rows.items(), key=lambda kv: -kv[1]["tokens"]):
                print(f"    {two:<4}{row['script']:<12}{row['tokens']/english:>6.2f}x")
        report[name] = rows

    if arguments.out:
        pathlib.Path(arguments.out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwritten to {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
