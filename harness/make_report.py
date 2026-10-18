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
import sys

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness.textreport.extras import agentic_page, tokenizer_page
from harness.textreport.loading import loading_page
from harness.textreport.quality import quality_page
from harness.textreport.speed import latency_page, throughput_page
from harness.textreport.table import tested

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


def main() -> int:
    """Write every result page from the results folder."""
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
    agentic_page(results, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
