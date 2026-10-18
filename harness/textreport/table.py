"""What every result page shares: column headers with their definitions, cells, page files."""

from __future__ import annotations

import functools
import pathlib
import re
from string import Template

# Each page's fixed text lives in `prose/<page>.md`, as `<!-- name -->` sections,
# so it is edited as text; the code adds the tables and the computed numbers.
PROSE = pathlib.Path(__file__).with_name("prose")
MARKER = re.compile(r"<!-- (\w+) -->")

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
    """A table cell: a dash for nothing, floats to `digits` places."""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def tested(summary: dict) -> list[dict]:
    """The models that were tested and loaded, by model then engine."""
    rows = [e for e in summary.values()
            if e.get("tested") and e.get("load", {}).get("ok")]
    rows.sort(key=lambda e: (e.get("model", ""), e.get("engine", "")))
    return rows


def page(path: pathlib.Path, title: str, lines: list[str]) -> None:
    """Write one page with its title."""
    path.write_text("\n".join([f"# {title}", ""] + lines) + "\n", encoding="utf-8")
    print(f"  {path}")


def ladder(entry: dict, key: str):
    """Items per second at concurrency 1, 8, 32 and 64, and the gain from first to best."""
    curve = entry.get(key) or {}
    rates = {c: curve.get(c, {}).get("items_per_s") for c in ("1", "8", "32", "64")}
    known = [v for v in rates.values() if v]
    gain = f"{max(known)/min(known):.1f}×" if len(known) > 1 else "—"
    return rates, gain


@functools.cache
def sections(name: str) -> dict[str, tuple[str, ...]]:
    """The sections of `prose/<name>.md`, each as its lines."""
    found: dict[str, list[str]] = {}
    current: list[str] = []
    for line in (PROSE / f"{name}.md").read_text(encoding="utf-8").split("\n")[:-1]:
        marker = MARKER.fullmatch(line)
        if marker:
            current = found.setdefault(marker.group(1), [])
        else:
            current.append(line)
    return {key: tuple(lines) for key, lines in found.items()}


def prose(name: str, section: str, **values: object) -> list[str]:
    """One section of a page's fixed text, with its `${value}` slots filled."""
    return [Template(line).substitute(values) for line in sections(name)[section]]
