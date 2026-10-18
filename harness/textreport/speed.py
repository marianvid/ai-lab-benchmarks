"""The throughput and latency pages: work per second, and one request at a time.

The pages' fixed text is in `prose/speed.md`; this adds the tables.
"""

from __future__ import annotations

import functools
import pathlib

from .table import cell, header, ladder, page, prose

RUNGS = ("1", "8", "32", "64")
LADDER_HEADER = ["| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |",
                 "|---|---|---:|---:|---:|---:|---:|"]
PREFILL_HEADER = ["| Model | Engine | c=1 | c=8 | c=32 | c=64 |",
                  "|---|---|---:|---:|---:|---:|"]
NOT_MEASURED = "Not yet measured in this run."

# The three prompt sizes `bench.py` sends, by the name it records them under.
SIZES = ("short prompt (~500 tok)", "medium prompt (~9k tok)", "long prompt (~29k tok)")


def rate_rows(rows: list[dict], key: str) -> list[str]:
    """One row per combination with a ladder under `key`: its rate at each rung and its gain."""
    lines = []
    for entry in rows:
        if not entry.get(key):
            continue
        rates, gain = ladder(entry, key)
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + " | ".join(cell(rates[c], 1) for c in RUNGS)
                     + f" | **{gain}** |")
    return lines


def prefill_rows(rows: list[dict]) -> list[str]:
    """One row per combination with a long-prompt ladder: its prefill rate at each rung."""
    lines = []
    for entry in rows:
        curve = entry.get("longform_curve")
        if not curve:
            continue
        lines.append(
            f"| {entry['model']} | {entry['engine']} | "
            + " | ".join(cell((curve.get(c) or {}).get("prefill_tok_s"), 1)
                         for c in RUNGS) + " |")
    return lines


# One section of these pages' fixed text: text(section, **values).
text = functools.partial(prose, "speed")


def long_prompts(rows: list[dict]) -> list[str]:
    """The long-prompt ladders, or a note that they were not measured."""
    if not any(e.get("longform_curve") for e in rows):
        return ["## Long prompts — whole articles", "", NOT_MEASURED, ""]
    return [*text("long_heading"), *LADDER_HEADER, *rate_rows(rows, "longform_curve"),
            *text("long_notes"),
            *text("prefill_heading", prefill=header("Prefill", "tok/s")), *PREFILL_HEADER,
            *prefill_rows(rows), *text("prefill_notes")]


def throughput_page(rows: list[dict], out: pathlib.Path) -> None:
    """Write `throughput.md`: work per second at each concurrency, short and long prompts."""
    page(out / "throughput.md", "Throughput",
         [*text("throughput_intro"), *LADDER_HEADER, *rate_rows(rows, "throughput_curve"),
          *text("short_notes"), *long_prompts(rows)])


def latency_row(entry: dict, size: str) -> str:
    """One combination's figures at one prompt size, or why there are none."""
    run = next((r for r in entry["latency"]["runs"] if r.get("test") == size), None)
    if not run or "error" in run:
        why = (run or {}).get("error", "not run")
        return f"| {entry['model']} | {entry['engine']} | — | — | — | {str(why)[:44]} |"
    return (f"| {entry['model']} | {entry['engine']} | {run.get('prompt_tokens')} "
            f"| {cell(run.get('ttft_s'), 2)} s | {cell(run.get('prefill_tok_s'), 1)} "
            f"| {cell(run.get('decode_tok_s'), 1)} |")


def latency_table(have: list[dict], size: str) -> list[str]:
    """The table for one prompt size."""
    return [f"## {size}", "",
            f"| Model | Engine | Prompt tokens | {header('TTFT')} "
            f"| {header('Prefill')} | {header('Decode')} |",
            "|---|---|---:|---:|---:|---:|",
            *(latency_row(entry, size) for entry in have), ""]


def latency_page(rows: list[dict], out: pathlib.Path) -> None:
    """Write `latency.md`: one request at a time, at three prompt lengths."""
    have = [e for e in rows if (e.get("latency") or {}).get("runs")]
    lines = text("latency_intro")
    if not have:
        lines.append(NOT_MEASURED)
    else:
        lines += [line for size in SIZES for line in latency_table(have, size)]
        lines += text("latency_notes")
    page(out / "latency.md", "Latency and prompt reading", lines)
