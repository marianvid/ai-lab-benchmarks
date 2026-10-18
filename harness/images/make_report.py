#!/usr/bin/env python3
"""Build the combined visual Linux and macOS image/OCR results page."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from string import Template

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.lab import LOOPBACK

# The port of the isolated manager the macOS run used: a fact of that run,
# reported, not a setting.
MAC_RUN_MANAGER_PORT = 8110

DIRECT = (
    ("sd15-smoke", "SD 1.5"),
    ("qwen-image-benchmark", "Qwen Image"),
    ("flux2-benchmark", "FLUX.2 Dev FP8 (legacy)"),
    ("flux2-dev-q8-benchmark", "FLUX.2 Dev 32B Q8_0"),
    ("flux2-dev-bf16-benchmark", "FLUX.2 Dev 32B BF16"),
)
MAC_ONLY = (
    ("flux2-klein-4b-benchmark", "FLUX.2 Klein 4B BF16"),
)
TITLES = {
    "composition": "Objects, colours and placement",
    "typography": "Exact text",
    "spatial": "Spatial instructions",
    "character-sheet": "Character consistency",
    "romanian-scene": "Photorealistic Romanian scene",
    "mug-color": "Change one object's colour",
    "notebook-label": "Add exact text without changing anything else",
    "background-change": "Replace only the background",
}
OCR_TITLES = {
    "clean": "Clean headline",
    "document": "Document-style text",
    "small_text": "Small technical text",
    "degraded": "Noisy, rotated and blurred text",
}
AI_LAB = "[AI-Lab](https://github.com/marianvid/ai-lab)"
MINUTE_S = 60


def load(path: str) -> dict:
    """A JSON file."""
    return json.loads(Path(path).read_text())


def cases(summary: dict, profile: str) -> dict[str, dict]:
    """One profile's cases, by case id."""
    return {row["case"]: row for row in summary["profiles"][profile]["cases"]}


def elapsed(seconds: float) -> str:
    """Seconds as seconds, or as minutes and seconds past one minute."""
    if seconds < MINUTE_S:
        return f"{seconds:.2f} s"
    minutes = int(seconds // MINUTE_S)
    return f"{minutes} min {seconds - minutes * MINUTE_S:.0f} s"


def review(row: dict) -> tuple[bool | None, int | None, int | None, str]:
    """A case's manual review: passed, score, maximum and note (all None when not reviewed)."""
    value = row.get("semantic_review") or {}
    if value.get("status") != "complete":
        return None, None, None, ""
    scores = value.get("criteria") or value.get("scores") or {}
    score = value.get("score", sum(bool(item) for item in scores.values()))
    maximum = value.get("max_score", len(scores))
    return bool(value.get("passed")), score, maximum, value.get("notes", "")


def image_cell(row: dict | None, prefix: str, label: str) -> str:
    """A table cell with the image, its time and its review verdict."""
    if not row or not row.get("ok"):
        reason = "No image: FP8 is unsupported by the Mac runtime" if "FLUX" in label else "No image produced"
        return f"**{html.escape(label)}**<br>{reason}"
    passed, score, maximum, _ = review(row)
    verdict = "Pass" if passed else "Needs attention"
    return (
        f'<img src="{prefix}/{row["artifact"]}" width="220" alt="{html.escape(label)}"><br>'
        f"**{html.escape(label)}**<br>{elapsed(row['duration_ms'] / 1000)} · "
        f"{score}/{maximum} criteria · **{verdict}**"
    )


def notes(labelled_rows: list[tuple[str, dict | None]]) -> list[str]:
    """The review notes of cases that need attention, one bullet each."""
    output = []
    for label, row in labelled_rows:
        if row:
            passed, _, _, note = review(row)
            if passed is False and note:
                output.append(f"- **{label}:** {note}")
    return output


def ocr_cell(row: dict) -> str:
    """A table cell with an OCR result: time, exact or not, CER and the text read."""
    verdict = "Exact" if row["exact_match"] else "Difference"
    return (
        f"**{elapsed(row['duration_seconds'])} · {verdict}**<br>"
        f"CER {row['cer']:.4f}<br>Recognised: `{html.escape(row['recognized'])}`"
    )


def profile_summary(summary: dict, profile: str) -> tuple[int, int, int, float]:
    """One profile's completed, total, passed, and mean seconds per image."""
    rows = summary["profiles"][profile]["cases"]
    completed = [row for row in rows if row.get("ok")]
    passed = sum(review(row)[0] is True for row in completed)
    mean = sum(row["duration_ms"] for row in completed) / max(1, len(completed)) / 1000
    return len(completed), len(rows), passed, mean


# The page's fixed text, with a `${name}` slot for each generated section.
TEMPLATE = Path(__file__).with_name("report-template.md")

# The Mac profiles in the summary table, with what each is good for.
MAC_PROFILES = (
    ("sd15-smoke", "SD 1.5", "Fast baseline, weak adherence"),
    ("qwen-image-benchmark", "Qwen Image", "Excellent quality, very slow"),
    ("flux2-klein-4b-benchmark", "FLUX.2 Klein 4B", "Best interactive option"),
    ("flux2-dev-q8-benchmark", "FLUX.2 Dev Q8_0", "Best full-size balance"),
    ("flux2-dev-bf16-benchmark", "FLUX.2 Dev BF16", "Full-precision reference"),
    ("qwen-edit-benchmark", "Qwen Image Edit", "Works locally; queue long jobs"),
)
OCR_MODELS = (("ocr-smoke", "Mobile detector"), ("ocr-server", "Server detector"))
LINUX_IMAGES = "../results/images"
MAC_IMAGES = "../results/images/macos"


def differences(found: list[str], heading: str = "**Visible differences:**") -> list[str]:
    """The notes under a table, when there are any."""
    return ["", heading, "", *found] if found else []


def checked(item: dict, kind: str) -> list[str]:
    """A test's heading, its prompt and what was checked."""
    return ["", f"### {TITLES[item['id']]}", "",
            f"> **{kind}:** {item['prompt']}", "",
            "**Checked:** " + "; ".join(item["rubric"]) + ".", ""]


def generation_case(item: dict, linux: dict, mac: dict) -> list[str]:
    """One generation prompt: the Linux–Mac table and the Mac-only table."""
    case_id = item["id"]
    lines = [*checked(item, "Prompt"),
             "#### Same model on Linux and Mac", "",
             "| Model | Linux · RTX PRO 4500 | Mac · M3 Max |",
             "|---|---|---|"]
    direct_notes: list[str] = []
    for profile, label in DIRECT:
        left = cases(linux, profile).get(case_id)
        right = cases(mac, profile).get(case_id)
        lines.append(f"| **{label}** | {image_cell(left, LINUX_IMAGES, label)} "
                     f"| {image_cell(right, MAC_IMAGES, label)} |")
        direct_notes += notes([(f"{label} on Linux", left), (f"{label} on Mac", right)])
    lines += differences(direct_notes)
    lines += ["", "#### Additional Mac-only FLUX options", "", "| Model | Mac result |", "|---|---|"]
    mac_notes: list[str] = []
    for profile, label in MAC_ONLY:
        row = cases(mac, profile).get(case_id)
        lines.append(f"| **{label}** | {image_cell(row, MAC_IMAGES, label)} |")
        mac_notes += notes([(label, row)])
    return lines + differences(mac_notes)


def editing(definitions: dict, linux: dict, mac: dict) -> list[str]:
    """Every edit, Linux beside Mac."""
    linux_edits = cases(linux, "qwen-edit-benchmark")
    mac_edits = cases(mac, "qwen-edit-benchmark")
    label = "Qwen Image Edit BF16"
    lines: list[str] = []
    for item in definitions["edits"]:
        left, right = linux_edits[item["id"]], mac_edits[item["id"]]
        lines += [*checked(item, "Instruction"),
                  "| Linux · RTX PRO 4500 | Mac · M3 Max |",
                  "|---|---|",
                  f"| {image_cell(left, LINUX_IMAGES, label)} "
                  f"| {image_cell(right, MAC_IMAGES, label)} |"]
        lines += differences(notes([("Linux", left), ("Mac", right)]),
                             "**Visible difference:**")
    return lines


def ocr(linux_ocr: dict, mac_ocr: dict) -> list[str]:
    """Every OCR fixture, both detectors, Linux beside Mac."""
    linux_rows = {(row["model"], row["case"]): row for row in linux_ocr["cases"]}
    mac_rows = {(row["model"], row["case"]): row for row in mac_ocr["cases"]}
    expected = {row["case"]: row["expected"] for row in linux_ocr["cases"]}
    lines: list[str] = []
    for case_id, title in OCR_TITLES.items():
        lines += [
            "", f"### {title}", "",
            f'<img src="../results/images/ocr/fixtures/{case_id}.png" width="560" alt="{title}">', "",
            f"**Expected:** `{html.escape(expected[case_id])}`", "",
            "| OCR model | Linux | Mac |", "|---|---|---|",
        ]
        lines += [f"| **{label}** | {ocr_cell(linux_rows[(model, case_id)])} "
                  f"| {ocr_cell(mac_rows[(model, case_id)])} |"
                  for model, label in OCR_MODELS]
    return lines


def glance(mac: dict) -> list[str]:
    """One row per Mac profile: completed, passed, mean time."""
    lines = []
    for profile, label, practical in MAC_PROFILES:
        completed, total, passed, mean = profile_summary(mac, profile)
        lines.append(f"| {label} | {completed}/{total} | {passed}/{completed} "
                     f"| {elapsed(mean)} | {practical} |")
    return lines


def joined(lines: list[str]) -> str:
    """Lines to follow the template text they are placed after."""
    return "".join("\n" + line for line in lines)


def main() -> int:
    """Write the combined Linux and macOS image and OCR page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-images", default="results/images/summary.json")
    parser.add_argument("--mac-images", default="results/images/macos/summary.json")
    parser.add_argument("--linux-ocr", default="results/images/ocr/results.json")
    parser.add_argument("--mac-ocr", default="results/images/macos/ocr/results.json")
    parser.add_argument("--cases", default="harness/images/cases.json")
    parser.add_argument("--out", default="docs/images-ocr.md")
    args = parser.parse_args()

    linux, mac = load(args.linux_images), load(args.mac_images)
    definitions = load(args.cases)
    generation = [line for item in definitions["generation"]
                  for line in generation_case(item, linux, mac)]
    page = Template(TEMPLATE.read_text()).substitute(
        ai_lab=AI_LAB, manager=f"{LOOPBACK}:{MAC_RUN_MANAGER_PORT}",
        generation=joined(generation),
        editing=joined(editing(definitions, linux, mac)),
        ocr=joined(ocr(load(args.linux_ocr), load(args.mac_ocr))),
        glance=joined(glance(mac)))
    Path(args.out).write_text(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
