#!/usr/bin/env python3
"""Validate recorded semantic reviews and merge them into the image summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def reviewed(case: dict, review: dict, document: dict, where: str) -> dict:
    """The semantic-review record for one case, after checking its rubric."""
    criteria = review["criteria"]
    if list(criteria) != case["rubric"]:
        raise RuntimeError(f"rubric drift: {where}")
    score = sum(bool(value) for value in criteria.values())
    maximum = len(criteria)
    return {
        "status": "complete",
        "passed": score == maximum,
        "score": score,
        "max_score": maximum,
        "criteria": criteria,
        "notes": review["notes"],
        "reviewer": document["reviewer"],
        "reviewed_at": document["reviewed_at"],
    }


def merge(summary: dict, document: dict) -> list[dict]:
    """Attach every review to its case; the review records, in order."""
    reviews = document["profiles"]
    if set(reviews) != set(summary["profiles"]):
        raise RuntimeError("semantic review profile set does not match the result summary")
    records = []
    for profile, entry in summary["profiles"].items():
        expected_cases = {case["case"] for case in entry["cases"]}
        if set(reviews[profile]) != expected_cases:
            raise RuntimeError(f"semantic review case set does not match {profile}")
        for case in entry["cases"]:
            case["semantic_review"] = reviewed(case, reviews[profile][case["case"]],
                                               document, f"{profile}/{case['case']}")
            records.append(case["semantic_review"])
    return records


def totals(records: list[dict]) -> dict:
    """How many cases and criteria passed, over all the reviews."""
    completed = len(records)
    passed = sum(int(record["passed"]) for record in records)
    return {
        "completed": completed,
        "total": completed,
        "passed_cases": passed,
        "failed_cases": completed - passed,
        "criteria_passed": sum(record["score"] for record in records),
        "criteria_total": sum(record["max_score"] for record in records),
    }


def main() -> int:
    """Copy the manual semantic reviews into the image summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/images/summary.json")
    parser.add_argument("--reviews", default="results/images/semantic-review.json")
    args = parser.parse_args()

    summary_path = Path(args.summary)
    summary = json.loads(summary_path.read_text())
    records = merge(summary, json.loads(Path(args.reviews).read_text()))
    summary["semantic_review_summary"] = totals(records)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
