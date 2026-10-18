"""The tokenizer-cost and agentic-coding pages.

The pages' fixed text is in `prose/extras.md`; this adds the tables and the numbers.
"""

from __future__ import annotations

import json
import functools
import pathlib

from .table import page, prose


TOKEN_HEADER = ["| Language | Script | Characters per token | Tokens vs English |",
                "|---|---|---:|---:|"]
AGENTIC_HEADER = ["| Model | Passed | Wall | Prompt tokens | Completion tokens | Tool turns |",
                  "|---|---:|---:|---:|---:|---:|"]

# The label each agentic run was recorded under, and the name shown for it.
AGENTIC_NAMES = {
    "qwen3.8-27b-q6-k": "Qwen3.8-27B Q6_K",
    "qwen3.8-27b-q8-0": "Qwen3.8-27B Q8_0",
    "qwopus3.6-27b-coder-q5-k-m": "Qwopus3.6-27B-Coder Q5_K_M",
}


# One section of these pages' fixed text: text(section, **values).
text = functools.partial(prose, "extras")


def token_rows(rows: dict, english: int) -> list[str]:
    """One row per language, most expensive first."""
    return [f"| {lang} | {row['script']} | {row['chars_per_token']} "
            f"| **{row['tokens']/english:.2f}×** |"
            for lang, row in sorted(rows.items(), key=lambda kv: -kv[1]["tokens"])]


def tokenizer_page(results: pathlib.Path, out: pathlib.Path) -> None:
    """Write `tokenizer.md`: what the same text costs in each writing system."""
    path = results / "tokens-per-script.json"
    if not path.exists():
        return
    tokens = json.loads(path.read_text())
    for model_name, rows in tokens.items():
        english = rows.get("en", {}).get("tokens")
        if not english:
            continue
        worst = max(rows.items(), key=lambda kv: kv[1]["tokens"])
        share = english / max(r["tokens"] for r in rows.values())
        page(out / "tokenizer.md", "Tokenizer cost by language",
             [*text("tokenizer_intro", model=model_name), *TOKEN_HEADER,
              *token_rows(rows, english),
              *text("token_notes", language=worst[0], script=worst[1]["script"],
                    share=f"{share:.0%}")])
        return


def shown(run: dict) -> str:
    """The name a run is shown under."""
    return AGENTIC_NAMES.get(run["label"], run["label"])


def run_totals(runs: list[dict]) -> list[str]:
    """One row per run: tasks passed, wall time, tokens and tool turns."""
    lines = []
    for run in runs:
        rows = run["tasks"]
        lines.append(
            f"| {shown(run)} "
            f"| {run['summary']['passed']}/{run['summary']['total']} "
            f"| {run['summary']['wall_s']:.1f} s "
            f"| {sum(row['usage']['prompt_tokens'] for row in rows):,} "
            f"| {sum(row['usage']['completion_tokens'] for row in rows):,} "
            f"| {sum(row['turns'] for row in rows)} |")
    return lines


def per_task(runs: list[dict]) -> list[str]:
    """Pass or fail for every run and task."""
    tasks = [row["task"] for row in runs[0]["tasks"]]
    lines = ["", "## Per task", "", "| Model | " + " | ".join(tasks) + " |",
             "|---|" + "---:|" * len(tasks)]
    for run in runs:
        marks = ["pass" if row["passed"] else "fail" for row in run["tasks"]]
        lines.append(f"| {shown(run)} | " + " | ".join(marks) + " |")
    return lines


def agentic_page(results: pathlib.Path, out: pathlib.Path) -> None:
    """Write `agentic-coding.md`: the architect-directed repository tasks."""
    directory = results / "qwen38-agentic"
    paths = sorted(directory.glob("*-agentic.json"))
    if not paths:
        return
    runs = [json.loads(path.read_text()) for path in paths]
    page(out / "agentic-coding.md", "Agentic coding probe",
         [*text("agentic_intro"), *AGENTIC_HEADER, *run_totals(runs), *per_task(runs),
          *text("agentic_findings"), *text("why_qwen38")])
