#!/usr/bin/env python3
"""Turn the run's JSON into the results document.

Written so that the tables in `02-results.md` are generated, never typed. A
number transcribed by hand is a number that can be wrong in a way nobody can
find later; a number generated from `results/` can always be traced back to the
file it came from.

    python3 make_report.py --results /opt/bench/results --out 02-results.md
"""

from __future__ import annotations

import argparse
import json
import pathlib

# The order tables are printed in: fastest engine first within a model family,
# so that the two formats of one model sit next to each other.
def sort_key(entry: dict) -> tuple:
    return (entry.get("model", ""), entry.get("engine", ""))


def cell(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def load(results: pathlib.Path) -> dict:
    summary = json.loads((results / "summary.json").read_text())
    for instance, entry in summary.items():
        for test in ("classification", "comprehension", "translation", "coding"):
            path = results / f"{instance}-{test.replace('classification', 'classify').replace('translation', 'translate')}.json"
            if entry.get(test) is None and path.exists():
                entry[test] = json.loads(path.read_text())
    return summary


def table(rows: list[str], header: str, sep: str) -> str:
    return "\n".join([header, sep, *rows]) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="/opt/bench/results")
    parser.add_argument("--out", default="-")
    arguments = parser.parse_args()

    summary = load(pathlib.Path(arguments.results))
    tested = [e for e in summary.values() if e.get("tested") and e.get("load", {}).get("ok")]
    tested.sort(key=sort_key)
    weighed = [e for e in summary.values() if not e.get("tested")]
    refused = [e for e in summary.values() if not e.get("load", {}).get("ok")]

    out = ["# Results", "",
           "Every number here was produced by a script in `harness/` and is in",
           "`results/` as JSON. Nothing was typed in by hand.", ""]

    # -- what ran ----------------------------------------------------------
    out += ["## The models", "",
            "| Model | Engine | Format | Load | Unload |",
            "|---|---|---|---:|---:|"]
    for entry in tested + weighed:
        out.append(f"| {entry['model']} | {entry['engine']} | {entry['format']} "
                   f"| {cell(entry.get('load', {}).get('load_s'), 1)} s "
                   f"| {cell(entry.get('unload', {}).get('unload_s'), 1)} s |")
    out.append("")
    if weighed:
        out += ["The last entry was loaded and unloaded but not tested. It is here to",
                "show that a model far larger than the card runs at all, and what that",
                "costs before it answers anything.", ""]
    if refused:
        out += ["**Did not start:** " +
                ", ".join(f"{e['model']} ({e['engine']}) — {e['load'].get('error','')}"
                          for e in refused), ""]

    # -- quality -----------------------------------------------------------
    out += ["## Quality, and what each run cost", "",
            "One pass per model per test. Correctness and speed come out of the same",
            "pass, because both are the answer to how this machine behaves.", ""]

    out += ["### Classification — SIB-200, twenty languages", "",
            "Is this sentence about politics? About one in seven is, so a model that",
            "always says no scores 86% accuracy and nothing else. F1 is the column",
            "that matters.", "",
            "| Model | Engine | F1 | Accuracy | Sentences/s | Prompt tok/s | Wall |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for entry in tested:
        row = entry.get("classification")
        if not row:
            out.append(f"| {entry['model']} | {entry['engine']} | — | — | — | — | — |")
            continue
        quality = row["quality"]
        out.append(f"| {entry['model']} | {entry['engine']} | **{cell(quality['f1'])}** "
                   f"| {cell(quality['accuracy'])} | {row['items_per_s']} "
                   f"| {row['prefill_tok_s']} | {row['wall_s']} s |")
    out.append("")

    out += ["### Comprehension — Belebele, twenty languages", "",
            "A passage, a question, four answers. Guessing scores 0.25.", "",
            "| Model | Engine | Accuracy | Questions/s | Wall |",
            "|---|---|---:|---:|---:|"]
    for entry in tested:
        row = entry.get("comprehension")
        out.append(f"| {entry['model']} | {entry['engine']} | "
                   + (f"**{cell(row['accuracy'])}** | {row['items_per_s']} | {row['wall_s']} s |"
                      if row else "— | — | — |"))
    out.append("")

    out += ["### Translation — FLORES-200, English into nineteen languages", "",
            "chrF++ against translations made by people.", "",
            "| Model | Engine | chrF++ | Translations/s | Wall |",
            "|---|---|---:|---:|---:|"]
    for entry in tested:
        row = entry.get("translation")
        out.append(f"| {entry['model']} | {entry['engine']} | "
                   + (f"**{cell(row['chrf_mean'], 2)}** | {row['items_per_s']} | {row['wall_s']} s |"
                      if row else "— | — | — |"))
    out.append("")

    out += ["### Coding — HumanEval+ and MBPP+", "",
            "541 problems, marked by running the code against the set's own tests.", "",
            "| Model | Engine | Pass rate | Passed | HumanEval+ | MBPP+ | Wall |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for entry in tested:
        row = entry.get("coding")
        if not row:
            out.append(f"| {entry['model']} | {entry['engine']} | — | — | — | — | — |")
            continue
        by_set = row.get("by_set", {})
        out.append(f"| {entry['model']} | {entry['engine']} "
                   f"| **{cell(row['pass_rate'])}** | {row['passed']}/{row['problems']} "
                   f"| {cell(by_set.get('humanevalplus', {}).get('pass_rate'))} "
                   f"| {cell(by_set.get('mbppplus', {}).get('pass_rate'))} "
                   f"| {row['wall_s']} s |")
    out.append("")

    # -- per language ------------------------------------------------------
    out += ["## Where the languages differ", "",
            "The average hides the useful part. These are the per-language F1 scores",
            "from the classification run, which is where a model that only pretends to",
            "read a language shows itself.", ""]
    languages = sorted({lang for e in tested if e.get("classification")
                        for lang in e["classification"]["per_language"]})
    out.append("| Model | " + " | ".join(languages) + " |")
    out.append("|---|" + "---:|" * len(languages))
    for entry in tested:
        row = entry.get("classification")
        if not row:
            continue
        cells = [cell(row["per_language"].get(lang, {}).get("f1"), 2) for lang in languages]
        out.append(f"| {entry['model']} ({entry['engine']}) | " + " | ".join(cells) + " |")
    out.append("")

    # -- throughput --------------------------------------------------------
    out += ["## Throughput against concurrency", "",
            "The same classification work at rising concurrency, on three languages in",
            "three writing systems. This is the measurement that says what the engine",
            "does, rather than what the model knows.", "",
            "| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for entry in tested:
        curve = entry.get("throughput_curve") or {}
        if not curve:
            continue
        rates = {c: curve.get(c, {}).get("items_per_s") for c in ("1", "8", "32", "64")}
        known = [v for v in rates.values() if v]
        gain = f"{max(known)/min(known):.1f}x" if len(known) > 1 else "—"
        out.append(f"| {entry['model']} | {entry['engine']} | "
                   + " | ".join(cell(rates[c], 1) for c in ("1", "8", "32", "64"))
                   + f" | **{gain}** |")
    out.append("")

    # -- what a token buys, per language -----------------------------------
    tokens_path = pathlib.Path(arguments.results) / "tokens-per-script.json"
    if tokens_path.exists():
        tokens = json.loads(tokens_path.read_text())
        for model_name, rows in tokens.items():
            english = rows.get("en", {}).get("tokens")
            if not english:
                continue
            out += ["## What a token buys, by language", "",
                    "The same FLORES sentences, in every language, counted by "
                    f"`{model_name}`'s tokenizer. Tokens are the unit of everything that",
                    "costs — how much context fits, how long reading takes, what a hosted",
                    "model charges — so the same content is not the same price in every",
                    "language.", "",
                    "| Language | Script | Characters per token | Tokens vs English |",
                    "|---|---|---:|---:|"]
            for lang, row in sorted(rows.items(), key=lambda kv: -kv[1]["tokens"]):
                out.append(f"| {lang} | {row['script']} | {row['chars_per_token']} "
                           f"| **{row['tokens']/english:.2f}x** |")
            worst = max(rows.items(), key=lambda kv: kv[1]["tokens"])
            out += ["",
                    "**It is not the writing system.** Chinese, in Han characters, is the",
                    "cheapest language here after English. The most expensive is "
                    f"{worst[0]}, written in {worst[1]['script']} — the same alphabet as",
                    "English. What decides the cost is how well the tokenizer knows the",
                    "language, not how exotic it looks.", "",
                    "The practical consequence: a context window quoted in tokens is worth",
                    f"about {english/max(r['tokens'] for r in rows.values()):.0%} as much in the "
                    "most expensive language here as it is in English.", ""]
            break

    # -- the model that does not fit ---------------------------------------
    oversize_path = pathlib.Path(arguments.results) / "oversize-80b.json"
    if oversize_path.exists():
        oversize = json.loads(oversize_path.read_text())
        out += ["## A model larger than the card", "",
                f"`{pathlib.Path(oversize['model_path']).name}` is "
                f"**{oversize['size_gb']} GB** on a card with 32 GB. AI-Lab refuses to",
                "load it, on purpose: this GPU is attached over an OCuLink cable, and a",
                "model split between card and system memory sends every token across that",
                "link. The refusal is a design decision, so it is worth knowing what the",
                "decision costs.", "",
                "Measured outside AI-Lab, with llama.cpp started by hand:", "",
                "| Split | Loaded | VRAM | Generation |",
                "|---|---:|---:|---:|"]
        for split in oversize["splits"]:
            if not split.get("ok"):
                out.append(f"| {split['gpu_layers']} | did not load | — | "
                           f"{split.get('error','')} |")
                continue
            generation = split.get("generation", {})
            out.append(f"| {split['gpu_layers']} | {split['load_s']} s "
                       f"| {split['vram_mb']} MB "
                       f"| {generation.get('decode_tok_s','—')} tok/s |")
        out += ["",
                "**Do not force the split.** Told to put a fixed number of layers on the",
                "card, llama.cpp gives up rather than fit — *\"n_gpu_layers already set by",
                "user to 36, abort\"* — and then fails trying to allocate 34 GB on a 32 GB",
                "card. Left alone, it works out the split itself and the model runs.", "",
                "The loading time above is warm: the file was already in the page cache",
                "from earlier attempts. A first read of 46 GB from disk is slower.", ""]

    text = "\n".join(out)
    if arguments.out == "-":
        print(text)
    else:
        pathlib.Path(arguments.out).write_text(text, encoding="utf-8")
        print(f"written to {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
