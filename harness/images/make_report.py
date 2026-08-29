#!/usr/bin/env python3
"""Build the combined visual Linux and macOS image/OCR results page."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


DIRECT = (
    ("sd15-smoke", "SD 1.5"),
    ("qwen-image-benchmark", "Qwen Image"),
    ("flux2-benchmark", "FLUX.2 Dev FP8 (legacy)"),
)
MAC_ONLY = (
    ("flux2-klein-4b-benchmark", "FLUX.2 Klein 4B BF16"),
    ("flux2-dev-q8-benchmark", "FLUX.2 Dev 32B Q8_0"),
    ("flux2-dev-bf16-benchmark", "FLUX.2 Dev 32B BF16"),
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


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def cases(summary: dict, profile: str) -> dict[str, dict]:
    return {row["case"]: row for row in summary["profiles"][profile]["cases"]}


def elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes = int(seconds // 60)
    return f"{minutes} min {seconds - minutes * 60:.0f} s"


def review(row: dict) -> tuple[bool | None, int | None, int | None, str]:
    value = row.get("semantic_review") or {}
    if value.get("status") != "complete":
        return None, None, None, ""
    scores = value.get("criteria") or value.get("scores") or {}
    score = value.get("score", sum(bool(item) for item in scores.values()))
    maximum = value.get("max_score", len(scores))
    return bool(value.get("passed")), score, maximum, value.get("notes", "")


def image_cell(row: dict | None, prefix: str, label: str) -> str:
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
    output = []
    for label, row in labelled_rows:
        if row:
            passed, _, _, note = review(row)
            if passed is False and note:
                output.append(f"- **{label}:** {note}")
    return output


def ocr_cell(row: dict) -> str:
    verdict = "Exact" if row["exact_match"] else "Difference"
    return (
        f"**{elapsed(row['duration_seconds'])} · {verdict}**<br>"
        f"CER {row['cer']:.4f}<br>Recognised: `{html.escape(row['recognized'])}`"
    )


def profile_summary(summary: dict, profile: str) -> tuple[int, int, int, float]:
    rows = summary["profiles"][profile]["cases"]
    completed = [row for row in rows if row.get("ok")]
    passed = sum(review(row)[0] is True for row in completed)
    mean = sum(row["duration_ms"] for row in completed) / max(1, len(completed)) / 1000
    return len(completed), len(rows), passed, mean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-images", default="results/images/summary.json")
    parser.add_argument("--mac-images", default="results/images/macos/summary.json")
    parser.add_argument("--linux-ocr", default="results/images/ocr/results.json")
    parser.add_argument("--mac-ocr", default="results/images/macos/ocr/results.json")
    parser.add_argument("--cases", default="harness/images/cases.json")
    parser.add_argument("--out", default="docs/images-ocr.md")
    args = parser.parse_args()

    linux = load(args.linux_images)
    mac = load(args.mac_images)
    linux_ocr = load(args.linux_ocr)
    mac_ocr = load(args.mac_ocr)
    definitions = load(args.cases)

    lines = [
        "# Images and OCR results",
        "",
        "This page contains the results themselves, not just links to raw files. Every image is shown with its model, processing time and prompt score. OCR shows the source, expected text and actual recognised text.",
        "",
        "> **How to read this page:** producing an image successfully is not the same as following the prompt. **Pass** means every visible requirement was met. Times come from one run, so use them as practical estimates rather than permanent rankings.",
        "",
        "## Complete test configuration",
        "",
        "These results measure the deployed **AI-Lab system**, including its gateway and engine adapter. They are not bare GPU kernel timings.",
        "",
        "| | Linux AI-Lab | macOS AI-Lab |",
        "|---|---|---|",
        "| Physical machine | AOOSTAR GEM12+ Pro | MacBook Pro `Mac15,9` |",
        "| CPU | AMD Ryzen 7 PRO 8845HS, 8 cores / 16 threads, 35 W target | Apple M3 Max, 16 CPU cores |",
        "| System memory | 96 GB DDR5-5600 | 128 GB unified memory |",
        "| GPU | NVIDIA RTX PRO 4500 Blackwell, 32 GB (32,623 MiB usable), ECC on, 200 W cap | Apple M3 Max, 40 GPU cores |",
        "| GPU connection | External OCuLink dock, about 8 GB/s while loading weights | Integrated unified-memory GPU |",
        "| Model storage | Two internal Lexar NM790 4 TB NVMe drives | Local/external AI-Lab model roots configured for the benchmark |",
        "| Operating environment | Proxmox VE host; engines run inside an **unprivileged LXC container** | macOS 15.7.3; AI-Lab runs natively, without LXC |",
        "| AI-Lab role | Gateway, model loading/unloading, request routing and timing | Native manager using an isolated benchmark configuration on `127.0.0.1:8110` |",
        "| Engine supervision | systemd, one unit per configured model instance | AI-Lab starts and supervises the local engine processes |",
        "| Image runtime | ComfyUI behind the private AI-Lab adapter; NVIDIA driver 610.57.04 and CUDA 13 | ComfyUI 0.34.0 behind the same adapter; Python 3.11.7, torch 2.13.0 and Apple MPS |",
        "| OCR runtime | PaddleOCR 3.x through AI-Lab's isolated OCR service | PaddleOCR 3.x in an isolated local runtime managed by AI-Lab |",
        "| Directly comparable tests | SD 1.5, Qwen Image, legacy FLUX.2, Qwen Image Edit, both OCR profiles | The same named tests and prompts |",
        "| Main trade-off | Much higher throughput | Enough shared memory for very large local models |",
        "",
        "The OCuLink connection affects model loading because weights cross the cable, but not image generation after the model is resident in GPU memory. Request timing includes the AI-Lab HTTP path and engine adapter because that is the system a real client uses.",
        "",
        "## Model settings",
        "",
        "Shared profiles use the same workflow settings on both computers. Fixed seeds give each pair the same random starting point.",
        "",
        "| Model | Size | Sampling | Role |",
        "|---|---:|---|---|",
        "| SD 1.5 | 512×512 | 20 steps, Euler, CFG 7 | Small, fast baseline |",
        "| Qwen Image | 1024×1024 | 50 steps, Euler/simple, CFG 4 | Detailed generation and exact text |",
        "| FLUX.2 Dev FP8 legacy | 1024×1024 | 20 steps, Euler | Direct compatibility test |",
        "| Qwen Image Edit BF16 | 1024×1024 source | 40 steps, Euler/simple, CFG 4 | Controlled edits |",
        "| FLUX.2 Klein 4B BF16 · Mac only | 1024×1024 | 4 steps, Euler, CFG 1 | Interactive generation |",
        "| FLUX.2 Dev Q8_0 / BF16 · Mac only | 1024×1024 | 20 steps, Euler | Full-size FLUX |",
        "",
        "## Image generation, test by test",
        "",
        "The first table under each prompt is the fair Linux–Mac comparison. Newer Mac-compatible FLUX options have no matching Linux run here, so they are shown separately rather than mixed into a misleading ranking.",
    ]

    for item in definitions["generation"]:
        case_id = item["id"]
        lines += [
            "", f"### {TITLES[case_id]}", "",
            f"> **Prompt:** {item['prompt']}", "",
            "**Checked:** " + "; ".join(item["rubric"]) + ".", "",
            "#### Same model on Linux and Mac", "",
            "| Model | Linux · RTX PRO 4500 | Mac · M3 Max |",
            "|---|---|---|",
        ]
        direct_notes: list[str] = []
        for profile, label in DIRECT:
            left = cases(linux, profile).get(case_id)
            right = cases(mac, profile).get(case_id)
            lines.append(f"| **{label}** | {image_cell(left, '../results/images', label)} | {image_cell(right, '../results/images/macos', label)} |")
            direct_notes += notes([(f"{label} on Linux", left), (f"{label} on Mac", right)])
        if direct_notes:
            lines += ["", "**Visible differences:**", "", *direct_notes]
        lines += ["", "#### Additional Mac-only FLUX options", "", "| Model | Mac result |", "|---|---|"]
        mac_notes: list[str] = []
        for profile, label in MAC_ONLY:
            row = cases(mac, profile).get(case_id)
            lines.append(f"| **{label}** | {image_cell(row, '../results/images/macos', label)} |")
            mac_notes += notes([(label, row)])
        if mac_notes:
            lines += ["", "**Visible differences:**", "", *mac_notes]

    lines += [
        "", "## Image editing, test by test", "",
        "Each platform edits its own Qwen Image composition. A good edit performs the requested change and leaves everything else untouched.",
    ]
    linux_edits = cases(linux, "qwen-edit-benchmark")
    mac_edits = cases(mac, "qwen-edit-benchmark")
    for item in definitions["edits"]:
        case_id = item["id"]
        lines += [
            "", f"### {TITLES[case_id]}", "",
            f"> **Instruction:** {item['prompt']}", "",
            "**Checked:** " + "; ".join(item["rubric"]) + ".", "",
            "| Linux · RTX PRO 4500 | Mac · M3 Max |",
            "|---|---|",
            f"| {image_cell(linux_edits[case_id], '../results/images', 'Qwen Image Edit BF16')} | {image_cell(mac_edits[case_id], '../results/images/macos', 'Qwen Image Edit BF16')} |",
        ]
        edit_notes = notes([("Linux", linux_edits[case_id]), ("Mac", mac_edits[case_id])])
        if edit_notes:
            lines += ["", "**Visible difference:**", "", *edit_notes]

    lines += [
        "", "## OCR, test by test", "",
        "OCR turns pixels into text. **Exact** means every character matches after normalising spacing and line breaks. **CER** is character error rate: 0 is perfect and lower is better. The mobile detector is smaller; the server detector is larger.",
        "",
        "The first Mac OCR row includes model start-up. This explains why the clean test is much slower than later images and matters mainly for occasional one-off use.",
    ]
    linux_rows = {(row["model"], row["case"]): row for row in linux_ocr["cases"]}
    mac_rows = {(row["model"], row["case"]): row for row in mac_ocr["cases"]}
    expected = {row["case"]: row["expected"] for row in linux_ocr["cases"]}
    for case_id in ("clean", "document", "small_text", "degraded"):
        lines += [
            "", f"### {OCR_TITLES[case_id]}", "",
            f'<img src="../results/images/ocr/fixtures/{case_id}.png" width="560" alt="{OCR_TITLES[case_id]}">', "",
            f"**Expected:** `{html.escape(expected[case_id])}`", "",
            "| OCR model | Linux | Mac |", "|---|---|---|",
        ]
        for model, label in (("ocr-smoke", "Mobile detector"), ("ocr-server", "Server detector")):
            lines.append(f"| **{label}** | {ocr_cell(linux_rows[(model, case_id)])} | {ocr_cell(mac_rows[(model, case_id)])} |")

    lines += [
        "", "## Mac results at a glance", "",
        "| Model | Completed | Prompt passes | Average time | Practical reading |",
        "|---|---:|---:|---:|---|",
    ]
    mac_profiles = (
        ("sd15-smoke", "SD 1.5", "Fast baseline, weak adherence"),
        ("qwen-image-benchmark", "Qwen Image", "Excellent quality, very slow"),
        ("flux2-klein-4b-benchmark", "FLUX.2 Klein 4B", "Best interactive option"),
        ("flux2-dev-q8-benchmark", "FLUX.2 Dev Q8_0", "Best full-size balance"),
        ("flux2-dev-bf16-benchmark", "FLUX.2 Dev BF16", "Full-precision reference"),
        ("qwen-edit-benchmark", "Qwen Image Edit", "Works locally; queue long jobs"),
    )
    for profile, label, practical in mac_profiles:
        completed, total, passed, mean = profile_summary(mac, profile)
        lines.append(f"| {label} | {completed}/{total} | {passed}/{completed} | {elapsed(mean)} | {practical} |")

    lines += [
        "", "## Advantages, disadvantages and recommendations", "",
        "### Linux workstation", "", "**Advantages**", "",
        "- About 32× faster for Qwen Image and 16× faster for Qwen Image Edit in these runs.",
        "- Runs the legacy FLUX.2 FP8 model successfully.",
        "- Qwen Image Edit passed all three preservation tests.",
        "- Low, predictable OCR latency after the service is available.",
        "", "**Disadvantages**", "",
        "- Dedicated GPU memory is limited to 32 GB, so very large workflows depend on quantisation or offloading.",
        "- SD 1.5 is fast but follows these detailed prompts poorly.",
        "", "### MacBook Pro", "", "**Advantages**", "",
        "- Its 128 GB unified memory runs FLUX.2 Dev BF16, Dev Q8_0, Qwen Image and Qwen Image Edit without OOM.",
        "- FLUX.2 Klein averages about 23 seconds and is the clear interactive choice.",
        "- Dev Q8_0 and BF16 both passed all 24 criteria; Q8_0 was 13.7% faster.",
        "- OCR quality is effectively identical to Linux on these fixtures.",
        "", "**Disadvantages**", "",
        "- Full-size generation takes roughly 17–20 minutes per image; Qwen editing takes roughly 42 minutes.",
        "- The older FLUX.2 FP8 format is incompatible with the Mac runtime; use Q8_0 or BF16.",
        "- OCR has a visible cold-start cost for occasional single images.",
        "", "### What to choose", "",
        "- **FLUX.2 Klein on Mac** for quick drafts and interactive work.",
        "- **FLUX.2 Dev Q8_0 on Mac** for full-size local FLUX; BF16 added time without improving this small rubric set.",
        "- **Qwen Image** when exact text and prompt adherence matter more than latency.",
        "- **Linux GPU** for volume generation or editing.",
        "- **Mobile OCR** for speed and degraded-text spacing; **server OCR** when exact clean-text recovery matters more than footprint.",
        "", "## Limits", "",
        "- Each image was generated once. These are evidence-backed practical timings, not statistical averages.",
        "- Mac-only FLUX Klein, Q8_0 and BF16 have no matching Linux run and are not presented as direct comparisons.",
        "- Qwen uses platform-specific runtimes and installed weight variants even though prompts and workflow settings match.",
        "- A prompt miss is a visible quality issue, not a crash or execution failure.",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
