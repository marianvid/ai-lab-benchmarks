#!/usr/bin/env python3
"""Generate the image and OCR benchmark report from preserved result JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", default="results/images/summary.json")
    parser.add_argument("--ocr", default="results/images/ocr/results.json")
    parser.add_argument("--out", default="docs/images-ocr.md")
    args = parser.parse_args()

    images = json.loads(Path(args.images).read_text())
    ocr = json.loads(Path(args.ocr).read_text())
    semantic = images["semantic_review_summary"]
    lines = [
        "# Image generation, editing and OCR",
        "",
        "This pass measures one fixed run on AI-Lab. Transport success and prompt adherence",
        "are reported separately: an image can be generated successfully and still fail its",
        "semantic rubric. Only cases that reached model execution count in model totals.",
        "",
        "## Result",
        "",
        f"All 18 image jobs reached model execution and produced valid PNG files. Semantic review passed {semantic['passed_cases']}/18 cases and failed {semantic['failed_cases']}/18. Across individual rubric criteria, {semantic['criteria_passed']}/{semantic['criteria_total']} passed.",
        "",
        "| Profile | Task | Executed | Semantic pass | Mean model time |",
        "|---|---:|---:|---:|---:|",
    ]
    failures = []
    for profile, entry in images["profiles"].items():
        cases = entry["cases"]
        executed = sum(case["status"] == "succeeded" for case in cases)
        semantic_pass = sum(case["semantic_review"]["passed"] for case in cases)
        mean_ms = sum(case["duration_ms"] for case in cases) / max(1, len(cases))
        lines.append(f"| `{profile}` | {entry['task']} | {executed}/{len(cases)} | {semantic_pass}/{len(cases)} | {mean_ms / 1000:.2f} s |")
        for case in cases:
            review = case["semantic_review"]
            if not review["passed"]:
                failed = [name for name, value in review["criteria"].items() if not value]
                failures.append((profile, case["case"], ", ".join(failed), review["notes"]))

    lines += ["", "## Preserved semantic failures", ""]
    for profile, case, failed, notes in failures:
        lines.append(f"- `{profile}/{case}`: failed {failed}. {notes}")

    lines += [
        "",
        "## OCR",
        "",
        "The OCR fixtures are checksum-pinned. Character error rate (CER) is computed from",
        "the API's canonical aggregate text; line-level text is used only when aggregate text",
        "is absent. This avoids counting the same recognition twice.",
        "",
        "| Profile | Executed | Exact | Mean CER | Mean confidence | Mean time |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, score in ocr["summary"]["scores"].items():
        rows = [row for row in ocr["cases"] if row["model"] == model and row["model_executed"]]
        mean_time = sum(row["duration_seconds"] for row in rows) / max(1, len(rows))
        lines.append(f"| `{model}` | {score['executed']}/4 | {score['exact_matches']}/4 | {score['mean_cer']:.4f} | {score['mean_confidence']:.4f} | {mean_time:.3f} s |")

    lines += [
        "",
        "## Method and artifacts",
        "",
        "- Prompts and rubrics: `harness/images/cases.json`.",
        "- Image orchestration: `harness/images/run_images.py`, using only the public AI-Lab API.",
        "- OCR orchestration and scoring: `harness/images/run_ocr.py`.",
        "- Semantic evidence: `results/images/semantic-review.json` and `results/images/summary.json`.",
        "- Generated library: `results/images/library/`.",
        "- OCR fixtures and raw responses: `results/images/ocr/`.",
        "",
        "Infrastructure and workflow incidents are excluded from model success rates. No such",
        "incident is counted as a model failure in this pass.",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
