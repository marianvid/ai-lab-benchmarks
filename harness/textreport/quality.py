"""The quality page: classification, comprehension, translation and coding scores.

The page's fixed text is in `prose/quality.md`; this adds the tables.
"""

from __future__ import annotations

import functools
import pathlib

from .table import cell, header, page, prose

TASKS = ("classification", "comprehension", "translation", "coding")


# One section of this page's fixed text: text(section, **values).
text = functools.partial(prose, "quality")


def missing(entry: dict, columns: int) -> str:
    """The row of a combination that has no result for this task."""
    return f"| {entry['model']} | {entry['engine']} | " + " | ".join(["—"] * columns) + " |"


def classification_table(rows: list[dict]) -> list[str]:
    """F1, accuracy and speed of every combination."""
    lines = [f"| Model | Engine | {header('F1')} | {header('Accuracy')} "
             f"| Sentences/s | {header('Prefill', 'tok/s')} "
             f"| {header('Wall', 's')} |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for entry in rows:
        row = entry.get("classification")
        if not row:
            lines.append(missing(entry, 5))
            continue
        quality = row["quality"]
        lines.append(
            f"| {entry['model']} | {entry['engine']} | **{cell(quality['f1'])}** "
            f"| {cell(quality['accuracy'])} | {row['items_per_s']} "
            f"| {row['prefill_tok_s']} | {row['wall_s']} |")
    return lines


def comprehension_table(rows: list[dict]) -> list[str]:
    """Accuracy, unanswered questions and speed of every combination."""
    lines = [f"| Model | Engine | {header('Accuracy')} | {header('Unanswered')} "
             f"| Questions/s | {header('Wall', 's')} |",
             "|---|---|---:|---:|---:|---:|"]
    for entry in rows:
        row = entry.get("comprehension")
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + (f"**{cell(row['accuracy'])}** "
                        f"| {row['of'] - row['answered']} | {row['items_per_s']} "
                        f"| {row['wall_s']} |" if row else "— | — | — | — |"))
    return lines


def translation_table(rows: list[dict]) -> list[str]:
    """chrF++ and speed of every combination."""
    lines = [f"| Model | Engine | {header('chrF++')} | Translations/s "
             f"| {header('Wall', 's')} |",
             "|---|---|---:|---:|---:|"]
    for entry in rows:
        row = entry.get("translation")
        lines.append(f"| {entry['model']} | {entry['engine']} | "
                     + (f"**{cell(row['chrf_mean'], 2)}** | {row['items_per_s']} "
                        f"| {row['wall_s']} |" if row else "— | — | — |"))
    return lines


def coding_table(rows: list[dict]) -> list[str]:
    """Pass rates, overall and per set, of every combination."""
    lines = [f"| Model | Engine | {header('Pass rate')} | Passed | HumanEval+ | MBPP+ "
             f"| {header('Wall', 's')} |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for entry in rows:
        row = entry.get("coding")
        if not row:
            lines.append(missing(entry, 5))
            continue
        by_set = row.get("by_set", {})
        lines.append(
            f"| {entry['model']} | {entry['engine']} | **{cell(row['pass_rate'])}** "
            f"| {row['passed']}/{row['problems']} "
            f"| {cell(by_set.get('humanevalplus', {}).get('pass_rate'))} "
            f"| {cell(by_set.get('mbppplus', {}).get('pass_rate'))} "
            f"| {row['wall_s']} |")
    return lines


def languages_table(rows: list[dict]) -> list[str]:
    """F1 per model and language."""
    languages = sorted({lang for e in rows if e.get("classification")
                        for lang in e["classification"]["per_language"]})
    lines = ["| Model | " + " | ".join(languages) + " |",
             "|---|" + "---:|" * len(languages)]
    for entry in rows:
        row = entry.get("classification")
        if not row:
            continue
        cells = [cell(row["per_language"].get(lang, {}).get("f1"), 2)
                 for lang in languages]
        lines.append(f"| {entry['model']} ({entry['engine']}) | "
                     + " | ".join(cells) + " |")
    return lines


def quality_page(rows: list[dict], out: pathlib.Path) -> None:
    """Write `quality.md`: classification, comprehension, translation and coding."""
    # Counted rather than written out. It was wrong the first time a model was
    # added, and a number in prose that nobody recomputes is a number that ages.
    complete = sum(all(entry.get(key) for key in TASKS) for entry in rows)
    partial = len(rows) - complete
    page(out / "quality.md", "Quality", [
        *text("intro", complete=complete, partial=partial), *text("how_to_read"),
        *text("classification"), *classification_table(rows), *text("classification_notes"),
        *text("comprehension"), *comprehension_table(rows), *text("comprehension_notes"),
        *text("gemma_misses"),
        *text("translation"), *translation_table(rows), *text("translation_notes"),
        *text("coding"), *coding_table(rows), *text("coding_notes"),
        *text("languages_intro"), *languages_table(rows), *text("languages_notes"),
    ])
