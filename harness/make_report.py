#!/usr/bin/env python3
"""Turn the run's JSON into the result pages under `docs/`.

The tables are generated, never typed. A number copied by hand can be wrong in a
way nobody finds later; a number generated from `results/` can always be traced
to the file it came from.

Output is several pages rather than one, because a single page of eight tables
is not something a person reads.

Column headers link into `docs/glossary.md` and carry the same short definition
as a link title, which most Markdown viewers show on hover. Longer notes go
*after* each table, where they explain numbers the reader has already seen.

    python3 make_report.py --results ./results --out ./docs
"""

from __future__ import annotations

import argparse
import json
import pathlib

# Column header -> (glossary anchor, hover text). Defined once, so a term reads
# the same everywhere it appears.
TERMS = {
    "F1": ("f1", "0-1, higher better. Precision and recall combined; used "
                 "because the set is only 15% positive"),
    "Accuracy": ("accuracy", "fraction answered correctly, 0-1"),
    "chrF++": ("chrf", "0-100, higher better. Overlap with a human reference "
                       "translation, counted in character sequences"),
    "Pass rate": ("pass-rate", "fraction of problems whose generated code ran "
                               "and passed every test"),
    "Prefill": ("prefill", "prompt reading, tokens per second"),
    "Decode": ("decode", "answer generation, tokens per second"),
    "TTFT": ("ttft", "time to first token, seconds"),
    "Wall": ("wall--wall-time", "seconds on a clock, start to finish"),
    "Items/s": ("items-per-second", "completed units of work per second"),
    "Unanswered": ("unanswered", "requests that produced no usable answer, out "
                                 "of 2 000. Counted as wrong, not dropped"),
}


def header(name: str, unit: str | None = None) -> str:
    """A column header: its name, a link to its definition, and its unit.

    The unit sits outside the link, so it is readable without hovering.
    Hovering was the only way to find out what a column held, which is no way
    to read a table.
    """
    text = name
    if name in TERMS:
        anchor, hover = TERMS[name]
        text = f'[{name}](glossary.md#{anchor} "{hover}")'
    return f"{text} ({unit})" if unit else text


def cell(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def load(results: pathlib.Path) -> dict:
    """summary.json, with every per-test result taken from its own file.

    The individual files win over the copy embedded in the summary. A test
    re-run on its own updates its file but not the summary, and the file is the
    one that was actually produced last.
    """
    summary = json.loads((results / "summary.json").read_text())
    files = {"classification": "classify", "comprehension": "comprehension",
             "translation": "translate", "coding": "coding", "latency": "latency"}
    for instance, entry in summary.items():
        for key, stem in files.items():
            path = results / f"{instance}-{stem}.json"
            if path.exists():
                entry[key] = json.loads(path.read_text())
        for prefix, field in (("throughput", "throughput_curve"),
                              ("longform", "longform_curve")):
            curve = {}
            for concurrency in ("1", "8", "32", "64"):
                path = results / f"{instance}-{prefix}-c{concurrency}.json"
                if path.exists():
                    row = json.loads(path.read_text())
                    curve[concurrency] = {k: row[k] for k in
                                          ("wall_s", "items_per_s",
                                           "prefill_tok_s", "decode_tok_s")}
            if curve:
                entry[field] = curve
    return summary


def tested(summary: dict) -> list[dict]:
    rows = [e for e in summary.values()
            if e.get("tested") and e.get("load", {}).get("ok")]
    rows.sort(key=lambda e: (e.get("model", ""), e.get("engine", "")))
    return rows


def page(path: pathlib.Path, title: str, lines: list[str]) -> None:
    path.write_text("\n".join([f"# {title}", ""] + lines) + "\n", encoding="utf-8")
    print(f"  {path}")


def ladder(entry: dict, key: str):
    curve = entry.get(key) or {}
    rates = {c: curve.get(c, {}).get("items_per_s") for c in ("1", "8", "32", "64")}
    known = [v for v in rates.values() if v]
    gain = f"{max(known)/min(known):.1f}×" if len(known) > 1 else "—"
    return rates, gain


# -- pages -------------------------------------------------------------------

def quality_page(rows: list[dict], out: pathlib.Path) -> None:
    # Counted rather than written out. It was wrong the first time a model was
    # added, and a number in prose that nobody recomputes is a number that ages.
    lines = [
        f"Four tasks, one pass each, across {len(rows)} model and engine "
        f"combinations.",
        "Each table gives the score and the time it took; both came out of the",
        "same run.",
        "",
        "See [method.md](method.md) for how each task was run and",
        "[models.md](models.md) for what the models are.",
        "",
        "## How to read these tables",
        "",
        "Every table has two kinds of column. The **score** says how well the",
        "model did; the **rate** and the **time** say how fast. They are",
        "independent — the fastest model here is not the most accurate one.",
        "",
        "| Column | What it measures | Range | Better |",
        "|---|---|---|---|",
        "| F1 | classification, balancing the ones it found against the ones it "
        "got right | 0 to 1 | higher |",
        "| Accuracy | the fraction of questions answered correctly | 0 to 1 "
        "| higher |",
        "| chrF++ | how much a translation overlaps a human one, counted in "
        "character sequences | 0 to 100 | higher |",
        "| Pass rate | the fraction of programs that ran and passed every test "
        "| 0 to 1 | higher |",
        "| HumanEval+, MBPP+ | the pass rate on each half of the coding set "
        "| 0 to 1 | higher |",
        "| Passed | problems passed, out of 541 | a count | higher |",
        "| Unanswered | questions that got no usable reply, out of 2 000 "
        "| a count | lower |",
        "| Sentences/s, Questions/s, Translations/s | items finished per second "
        "| per second | higher |",
        "| Prefill | how fast the model reads a prompt | tokens per second "
        "| higher |",
        "| Wall | how long the whole task took | seconds | lower |",
        "",
        "**A score near the bottom of its range is not a bad model, it is a",
        "hard task.** Comprehension is a choice between four answers, so 0.25",
        "is what guessing scores and the useful range starts there. Translation",
        "scores are held down by the languages in the set; see the caveat in",
        "the [README](../README.md).",
        "",
        "## Classification",
        "",
        "The model reads a sentence and answers one question: is its topic",
        "politics. 4 080 sentences in 20 languages, of which 15% are political.",
        "",
        f"| Model | Engine | {header('F1')} | {header('Accuracy')} "
        f"| Sentences/s | {header('Prefill', 'tok/s')} "
        f"| {header('Wall', 's')} |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for entry in rows:
        row = entry.get("classification")
        if not row:
            lines.append(f"| {entry['model']} | {entry['engine']} | — | — | — | — | — |")
            continue
        quality = row["quality"]
        lines.append(
            f"| {entry['model']} | {entry['engine']} | **{cell(quality['f1'])}** "
            f"| {cell(quality['accuracy'])} | {row['items_per_s']} "
            f"| {row['prefill_tok_s']} | {row['wall_s']} |")
    lines += [
        "",
        "**Accuracy is higher than F1 for every model, and the gap matters.**",
        "Only 15% of the sentences are political, so a model answering \"no\" to",
        "everything scores 0.85 accuracy and finds nothing. F1 collapses in that",
        "case; accuracy does not. Judge by F1.",
        "",
        "**Prefill here is not a long-prompt figure.** These are single sentences",
        "sent five to a request, a few hundred tokens each. For prompt reading at",
        "8 000 and 29 000 tokens see [latency.md](latency.md).",
        "",
        "**Wall time here is not a quality signal.** It is the same work, but",
        "llama.cpp ran it with eight requests in flight and gained nothing from",
        "that; see [throughput.md](throughput.md).",
        "",
        "## Comprehension",
        "",
        "A passage, a question about it, four answers of which one is right. The",
        "model replies with a single letter. 100 questions per language, 2 000 in",
        "total, always the same 100 so every model is asked the same things.",
        "",
        f"| Model | Engine | {header('Accuracy')} | {header('Unanswered')} "
        f"| Questions/s | {header('Wall', 's')} |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for entry in rows:
        row = entry.get("comprehension")
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + (f"**{cell(row['accuracy'])}** "
                        f"| {row['of'] - row['answered']} | {row['items_per_s']} "
                        f"| {row['wall_s']} |" if row else "— | — | — | — |"))
    lines += [
        "",
        "**Guessing scores 0.25**, because there are four options. Subtract it",
        "before comparing: 0.74 and 0.91 are not 23% apart, they are 0.49 and",
        "0.66 above chance, which is a third more.",
        "",
        "**This is where model size shows.** The smallest model loses far more",
        "here than on classification or coding. A passage has to be understood;",
        "it cannot be pattern-matched from a keyword.",
        "",
        "**Unanswered questions are counted as wrong.** The answer is read from",
        "the first eight tokens, and a model that writes anything other than a",
        "letter there has not answered. The score divides by all 2 000, so a",
        "model that fails to answer is penalised exactly as much as one that",
        "answers incorrectly — no model is flattered by the questions it skipped.",
        "",
        "**It is the two large Gemma models, on either engine.** Gemma-4-26B-A4B",
        "loses 43 both times; Gemma-4-31B loses 12 and 11. The same model loses",
        "about the same number whichever engine runs it, which puts the cause in",
        "the weights rather than in the engine or the harness. Gemma-4-E4B, the",
        "small one, loses none, and nothing else in the table loses more than 2.",
        "",
        "**They are a few questions, not a scatter.** The harness now records",
        "which question produced no letter and what came back instead. For",
        "Gemma-4-31B on llama.cpp the 12 misses are three questions: number 48 in",
        "nine languages, number 24 in two, and number 89 in one. See",
        "[the recorded misses](../results/gemma31-gguf-comprehension-misses.json).",
        "",
        "**What came back was an explanation rather than a letter.** On question",
        "48 the model began \"The provided passage lists ...\"; on 24 and 89,",
        "\"None of the options are correct based on ...\". Question 48 asks which",
        "of four activities does not reflect personal involvement, and none of",
        "the four appears anywhere in its passage.",
        "",
        "The system prompt tells the model the answer is always in the passage",
        "and not to object that it is incomplete. On these questions it objects",
        "anyway, the objection is cut off at eight tokens, and the score counts",
        "it wrong. That is a measurement of instruction-following, not of",
        "comprehension. Only Gemma-4-31B on llama.cpp has this recorded — the",
        "other runs predate the change and have counts only.",
        "",
        "## Translation",
        "",
        "English into 19 languages, 50 sentences each, 950 translations per",
        "model, scored against FLORES's human translations.",
        "",
        f"| Model | Engine | {header('chrF++')} | Translations/s "
        f"| {header('Wall', 's')} |",
        "|---|---|---:|---:|---:|",
    ]
    for entry in rows:
        row = entry.get("translation")
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + (f"**{cell(row['chrf_mean'], 2)}** | {row['items_per_s']} "
                        f"| {row['wall_s']} |" if row else "— | — | — |"))
    lines += [
        "",
        "**The values are low because the language mix is hard.** These 19",
        "include Tamil, Thai, Bengali and Lithuanian. A study covering only",
        "western European languages reports ten to fifteen points higher for the",
        "same models. Compare within this table only.",
        "",
        "**The references were made by people**, not generated. A score here is",
        "agreement with a human translator rather than with another model.",
        "",
        "## Coding",
        "",
        "541 Python problems. The generated code is executed against the tests",
        "that came with the problem; it passes or it does not.",
        "",
        f"| Model | Engine | {header('Pass rate')} | Passed | HumanEval+ | MBPP+ "
        f"| {header('Wall', 's')} |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for entry in rows:
        row = entry.get("coding")
        if not row:
            lines.append(f"| {entry['model']} | {entry['engine']} | — | — | — | — | — |")
            continue
        by_set = row.get("by_set", {})
        lines.append(
            f"| {entry['model']} | {entry['engine']} | **{cell(row['pass_rate'])}** "
            f"| {row['passed']}/{row['problems']} "
            f"| {cell(by_set.get('humanevalplus', {}).get('pass_rate'))} "
            f"| {cell(by_set.get('mbppplus', {}).get('pass_rate'))} "
            f"| {row['wall_s']} |")
    lines += [
        "",
        "**HumanEval+ scores higher than MBPP+ for every model.** HumanEval gives",
        "the function signature and a docstring to complete; MBPP describes the",
        "task in one sentence and pins the function name only through an example",
        "call. Less structure, more room to misread it.",
        "",
        "**These problems are in every model's training data.** They are old and",
        "public, so part of a score is memory rather than reasoning. That would",
        "invalidate a ranking of programmers; here they are a fixed, executable",
        "workload for measuring the configuration.",
        "",
        "**One problem is excluded.** HumanEval/32's own reference solution fails",
        "its own tests. All 164 references were run through this harness to check:",
        "163 pass. Leaving it in would deduct a point from every model for",
        "something none of them can pass.",
        "",
        "## Per-language classification scores",
        "",
        "The same classification run, split by the language of the sentence. Each",
        "language contributes 204 sentences, about 30 of them political.",
        "",
    ]
    languages = sorted({lang for e in rows if e.get("classification")
                        for lang in e["classification"]["per_language"]})
    lines.append("| Model | " + " | ".join(languages) + " |")
    lines.append("|---|" + "---:|" * len(languages))
    for entry in rows:
        row = entry.get("classification")
        if not row:
            continue
        cells = [cell(row["per_language"].get(lang, {}).get("f1"), 2)
                 for lang in languages]
        lines.append(f"| {entry['model']} ({entry['engine']}) | "
                     + " | ".join(cells) + " |")
    lines += [
        "",
        "A model can look competent on the average and be much weaker in one",
        "language. Read down a column rather than across a row.",
        "",
        "With about 30 positive examples per language, one misjudged sentence",
        "moves that language's F1 by roughly 0.015. Gaps under 0.03 between",
        "languages are noise.",
    ]
    page(out / "quality.md", "Quality", lines)


def throughput_page(rows: list[dict], out: pathlib.Path) -> None:
    lines = [
        "How much work each combination completes per second, and how that",
        "changes when more requests arrive at once.",
        "",
        "Two ladders, because prompt length changes the answer. Short prompts are",
        "single sentences; long prompts are whole Wikipedia articles of 2 000 to",
        "5 000 characters. The prompt fills the",
        "[KV cache](glossary.md#kv-cache), and the cache limits how many requests",
        "an engine holds at once.",
        "",
        "## Short prompts — sentences",
        "",
        "Classification on English, Russian and Chinese, repeated at 1, 8, 32 and",
        "64 requests in flight. Figures are sentences per second.",
        "",
        "| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for entry in rows:
        if not entry.get("throughput_curve"):
            continue
        rates, gain = ladder(entry, "throughput_curve")
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + " | ".join(cell(rates[c], 1) for c in ("1", "8", "32", "64"))
                     + f" | **{gain}** |")
    lines += [
        "",
        "**Gain is the highest rate divided by the lowest**: what the engine got",
        "out of being handed more work at once. A gain of 1.0 means nothing — the",
        "ninth request waited for one of the first eight to finish.",
        "",
        "**At one request at a time the engines are comparable.** The difference",
        "appears only under load, from",
        "[continuous batching](glossary.md#continuous-batching).",
        "",
        "**vLLM stops improving between 32 and 64**: the card is saturated, and",
        "further requests only wait longer.",
        "",
    ]
    if any(e.get("longform_curve") for e in rows):
        lines += [
            "## Long prompts — whole articles",
            "",
            "The same ladder, sending complete Wikipedia articles and asking for a",
            "one-word answer. Long input, short output: the shape of",
            "classification, routing and tagging work on real documents. 60",
            "articles per run, 2 165–5 227 characters, six languages.",
            "",
            "| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for entry in rows:
            if not entry.get("longform_curve"):
                continue
            rates, gain = ladder(entry, "longform_curve")
            lines.append(f"| {entry['model']} | {entry['engine']} | "
                         + " | ".join(cell(rates[c], 1) for c in ("1", "8", "32", "64"))
                         + f" | **{gain}** |")
        lines += [
            "",
            "**Compare the gain columns between the two tables, not the rates.**",
            "An article is ten to twenty times longer than a sentence, so fewer",
            "finish per second either way. What changes is whether the engine",
            "still profits from concurrency when each request holds far more",
            "cache — for some combinations it profits more, for others barely at",
            "all.",
            "",
        ]
    else:
        lines += ["## Long prompts — whole articles", "",
                  "Not yet measured in this run.", ""]
    page(out / "throughput.md", "Throughput", lines)


def latency_page(rows: list[dict], out: pathlib.Path) -> None:
    have = [e for e in rows if (e.get("latency") or {}).get("runs")]
    lines = [
        "One request at a time, at three prompt sizes. What a person or an agent",
        "waiting for a single answer experiences, and the only place here where",
        "long prompts are read.",
        "",
        "The prompt is Python source repeated to length, followed by a request",
        "to rewrite one function: the shape of an agent pasting a codebase into",
        "every turn.",
        "",
    ]
    if not have:
        lines.append("Not yet measured in this run.")
        page(out / "latency.md", "Latency and prompt reading", lines)
        return

    for size in ("short prompt (~500 tok)", "medium prompt (~9k tok)",
                 "long prompt (~29k tok)"):
        lines += [
            f"## {size}",
            "",
            f"| Model | Engine | Prompt tokens | {header('TTFT')} "
            f"| {header('Prefill')} | {header('Decode')} |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for entry in have:
            run = next((r for r in entry["latency"]["runs"]
                        if r.get("test") == size), None)
            if not run or "error" in run:
                why = (run or {}).get("error", "not run")
                lines.append(f"| {entry['model']} | {entry['engine']} | — | — | — "
                             f"| {str(why)[:44]} |")
                continue
            lines.append(
                f"| {entry['model']} | {entry['engine']} | {run.get('prompt_tokens')} "
                f"| {cell(run.get('ttft_s'), 2)} s | {cell(run.get('prefill_tok_s'), 1)} "
                f"| {cell(run.get('decode_tok_s'), 1)} |")
        lines.append("")
    lines += [
        "**The same text is a different number of tokens for each model.** The",
        "prompt is identical; the tokenizers are not. That column is the first",
        "place the difference in [tokenizer.md](tokenizer.md) becomes visible.",
        "",
        "**TTFT is the number a person feels.** On a long prompt it is almost",
        "all prompt reading — the model cannot start answering until it has read",
        "the question.",
        "",
        "**Prefill and decode do not move together.** Prefill processes every",
        "token of the prompt at once and reaches thousands per second; decode",
        "produces one token at a time and reaches tens. A machine can be strong",
        "at one and ordinary at the other, and which matters depends entirely on",
        "the work.",
        "",
        "**Prefill rates fall as prompts grow.** Attention cost rises faster than",
        "linearly with length, so reading 32 000 tokens is more than four times",
        "the work of reading 8 000.",
        "",
        "An error in the last table usually means the instance's",
        "[context window](glossary.md#context-window) was smaller than the",
        "prompt. All instances here were set to 32 768 tokens.",
    ]
    page(out / "latency.md", "Latency and prompt reading", lines)


def loading_page(summary: dict, results: pathlib.Path, out: pathlib.Path) -> None:
    rows = tested(summary)
    warm_measured = any((e.get("reload") or {}).get("load_s") for e in rows)
    lines = [
        "How long it takes to get a model onto the card and off it again.",
        "",
    ]
    if warm_measured:
        lines += [
            "Loading is measured twice. The **first load** happens with the file",
            "not in memory, so it includes reading 4 to 22 GB from the NVMe. The",
            "**reload** happens immediately afterwards, when the operating system",
            "still holds the file in its [page cache](glossary.md#page-cache) and",
            "the disk is skipped entirely.",
            "",
            "The host's page cache was dropped before the run, so the first loads",
            "are genuinely cold.",
            "",
        ]
    else:
        lines += [
            "**These are cold loads**: the host's page cache was dropped before",
            "the run, so each figure includes reading the weights from NVMe.",
            "",
        ]
    lines += [
        "| Model | Engine | On disk | First load (cold) | Reload (warm) | Unload |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for entry in rows:
        first = entry.get("load", {}).get("load_s")
        again = (entry.get("reload") or {}).get("load_s")
        size = entry.get("size_bytes")
        lines.append(
            f"| {entry['model']} | {entry['engine']} "
            f"| {(f'{size / 1024 ** 3:.1f} GB') if size else '—'} "
            f"| {cell(first, 1)} s "
            f"| {(cell(again, 1) + ' s') if again is not None else '—'} "
            f"| {cell(entry.get('unload', {}).get('unload_s'), 1)} s |")
    lines += [
        "",
        "**Reading the weights is a small part of a vLLM start.** Its own startup",
        "log puts the disk read at 9.3 seconds out of 111. The rest is importing",
        "torch and CUDA, profiling memory, compiling kernels, and — on a",
        "multimodal model — pushing invented images and audio through the model",
        "to measure those paths. [The vLLM start sequence]"
        "(vllm-startup.md) breaks it down phase by phase.",
        "",
        "**The cold-to-warm gaps above were not isolated.** They are inconsistent",
        "across models of similar size — 95 s for one, 5 s for another — so the",
        "disk does not account for them. The likeliest cause is vLLM's",
        "compiled-kernel cache: an empty one turned a 47-second start into 241",
        "seconds in a separate measurement.",
        "",
        "**72 of those 111 seconds are avoidable on a multimodal model.** The",
        "`--language-model-only` flag skips the multimodal profiling and warm-up",
        "and takes the same model from 111 seconds to 39, at a cost of about 6%",
        "of KV cache capacity. Details and the trade-off are on the same page.",
        "",
        "**llama.cpp starts in seconds, vLLM in a minute or more.** For work that",
        "loads a model, asks one question and unloads, llama.cpp finishes before",
        "vLLM has started. Under sustained batched work the advantage reverses;",
        "the crossover is around 90 seconds.",
        "",
        "**Unloading is uniform** and set by waiting for the driver to hand the",
        "memory back, not by the model's size.",
        "",
    ]
    refused = [e for e in summary.values() if not e.get("load", {}).get("ok")]
    if refused:
        lines += ["## Would not start", "",
                  "What the engine or the manager reported, verbatim.", ""]
        for entry in refused:
            lines.append(f"- **{entry['model']}** ({entry['engine']}): "
                         f"{entry['load'].get('error','')}")
        lines.append("")

    big = summary.get("coder-next-80b") or {}
    latency = big.get("latency") or {}
    if big.get("load", {}).get("ok"):
        size = big.get("size_bytes", 0) / 1024 ** 3
        runs = {r.get("test"): r for r in latency.get("runs", [])}
        lines += [
            "## A model larger than the card",
            "",
            f"Qwen3-Coder-Next in GGUF Q4 is {size:.1f} GB and the card holds",
            "32.6. llama.cpp puts as many layers on the card as fit and leaves",
            "the rest in system memory, reaching them over the cable for every",
            "token. It is set per instance: -1 keeps the whole model on the card",
            "and refuses to load if it does not fit, -2 lets llama.cpp work out",
            "how many layers fit.",
            "",
            f"| | {header('Wall', 's')} |",
            "|---|---:|",
            f"| First load (cold) | {cell(big['load'].get('load_s'), 1)} s |",
            f"| Reload (warm) | {cell((big.get('reload') or {}).get('load_s'), 1)} s |",
            f"| Unload | {cell((big.get('unload') or {}).get('unload_s'), 1)} s |",
            "",
            "Per gigabyte that is the same rate as a model that fits: 0.50",
            "seconds against 0.52 for Qwen3.6-35B at 20.6 GB. Loading is reading",
            "a file, and the part that stays in system memory never has to cross",
            "the cable at all.",
            "",
        ]
        if runs:
            lines += [
                f"| Prompt | {header('TTFT')} | {header('Prefill')} "
                f"| {header('Decode')} |",
                "|---|---:|---:|---:|",
            ]
            for name in ("short prompt (~500 tok)", "medium prompt (~9k tok)",
                         "long prompt (~29k tok)"):
                run = runs.get(name)
                if not run:
                    continue
                lines.append(
                    f"| {run['prompt_tokens']} tokens "
                    f"| {cell(run.get('ttft_s'), 2)} s "
                    f"| {cell(run.get('prefill_tok_s'), 1)} "
                    f"| {cell(run.get('decode_tok_s'), 1)} |")
            lines += [
                "",
                "**Generation barely notices.** 52 to 57 tokens per second,",
                "which is in the same range as models that fit entirely. Only a",
                "small share of a mixture-of-experts model is used for any one",
                "token, so most of what sits in system memory is never read.",
                "",
                "**Prompt reading is where it hurts.** 3 043 tokens per second",
                "on a short prompt, 291 on a medium one, 466 on a long one — not",
                "a straight line, and not measured often enough to say why the",
                "long prompt beats the medium one. What matters is the size of",
                "the drop: reading a prompt processes it all at once, so every",
                "layer sitting in system memory has the whole batch sent to it",
                "and back. A 29 000-token prompt takes 53 seconds before the",
                "first word of the answer.",
                "",
                "**So it suits generation, not long prompts.** Which is the wrong",
                "way round for an agent, since an agent sends whole files.",
                "",
            ]
        lines += [
            "**Let llama.cpp choose the split.** Given a number it will not",
            "adjust it: `n_gpu_layers already set by user to 28, abort`, followed",
            "by a failure to allocate 26 664 MiB on a 32 623 MiB card. With the",
            "setting left on -2 the flag is not passed at all, llama.cpp measures",
            "the free memory itself, and the model runs.",
        ]
    page(out / "loading.md", "Loading and unloading", lines)


def tokenizer_page(results: pathlib.Path, out: pathlib.Path) -> None:
    path = results / "tokens-per-script.json"
    if not path.exists():
        return
    tokens = json.loads(path.read_text())
    for model_name, rows in tokens.items():
        english = rows.get("en", {}).get("tokens")
        if not english:
            continue
        worst = max(rows.items(), key=lambda kv: kv[1]["tokens"])
        lines = [
            "How many [tokens](glossary.md#token) the same content costs in each",
            "language.",
            "",
            "This is not a quality measurement and needs no GPU. It counts the",
            "same 200 FLORES sentences — identical content in every language —",
            f"with `{model_name}`'s tokenizer.",
            "",
            "| Language | Script | Characters per token | Tokens vs English |",
            "|---|---|---:|---:|",
        ]
        for lang, row in sorted(rows.items(), key=lambda kv: -kv[1]["tokens"]):
            lines.append(f"| {lang} | {row['script']} | {row['chars_per_token']} "
                         f"| **{row['tokens']/english:.2f}×** |")
        lines += [
            "",
            "**The last column.** 1.50× means the same text costs half again as",
            "many tokens as in English: a context window holds two thirds as much",
            "of it, a request takes half again as long to read, and a hosted",
            "model charges half again as much.",
            "",
            "**The writing system does not predict the cost.** Chinese, in Han",
            "characters, is the cheapest language here after English. The most",
            f"expensive is {worst[0]}, written in {worst[1]['script']} — the same",
            "alphabet as English.",
            "",
            "What decides it is how much of that language the tokenizer was built",
            "from. One trained mostly on English and Chinese text holds whole",
            "Chinese words as single tokens and cuts Lithuanian into fragments.",
            "",
            "A context window sized against",
            f"English documents holds about "
            f"{english/max(r['tokens'] for r in rows.values()):.0%} as much "
            f"{worst[0]}. Size it on the most expensive language you will",
            "actually send, or requests will be rejected for length in a way that",
            "looks like a model fault.",
        ]
        page(out / "tokenizer.md", "Tokenizer cost by language", lines)
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="./results")
    parser.add_argument("--out", default="./docs")
    arguments = parser.parse_args()

    results = pathlib.Path(arguments.results)
    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)

    summary = load(results)
    rows = tested(summary)
    print(f"{len(rows)} combinations -> {out}")

    quality_page(rows, out)
    throughput_page(rows, out)
    latency_page(rows, out)
    loading_page(summary, results, out)
    tokenizer_page(results, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
