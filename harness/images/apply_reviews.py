#!/usr/bin/env python3
"""Validate recorded semantic reviews and merge them into the image summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/images/summary.json")
    parser.add_argument("--reviews", default="results/images/semantic-review.json")
    args = parser.parse_args()

    summary_path = Path(args.summary)
    summary = json.loads(summary_path.read_text())
    review_document = json.loads(Path(args.reviews).read_text())
    reviews = review_document["profiles"]
    completed = passed = criteria_passed = criteria_total = 0

    expected_profiles = set(summary["profiles"])
    if set(reviews) != expected_profiles:
        raise RuntimeError("semantic review profile set does not match the result summary")

    for profile, entry in summary["profiles"].items():
        expected_cases = {case["case"] for case in entry["cases"]}
        if set(reviews[profile]) != expected_cases:
            raise RuntimeError(f"semantic review case set does not match {profile}")
        for case in entry["cases"]:
            review = reviews[profile][case["case"]]
            criteria = review["criteria"]
            if list(criteria) != case["rubric"]:
                raise RuntimeError(f"rubric drift: {profile}/{case['case']}")
            score = sum(bool(value) for value in criteria.values())
            maximum = len(criteria)
            case_passed = score == maximum
            case["semantic_review"] = {
                "status": "complete",
                "passed": case_passed,
                "score": score,
                "max_score": maximum,
                "criteria": criteria,
                "notes": review["notes"],
                "reviewer": review_document["reviewer"],
                "reviewed_at": review_document["reviewed_at"],
            }
            completed += 1
            passed += int(case_passed)
            criteria_passed += score
            criteria_total += maximum

    summary["semantic_review_summary"] = {
        "completed": completed,
        "total": completed,
        "passed_cases": passed,
        "failed_cases": completed - passed,
        "criteria_passed": criteria_passed,
        "criteria_total": criteria_total,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
