#!/usr/bin/env python3
"""Run a reproducible PP-OCRv5 mobile/server comparison through AI-Lab."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.shared.lab import MANAGER_HELP, form_body, manager_url
from harness.shared.textmetrics import distance


CASES = (
    ("clean", ("AI LAB BENCHMARK 2026",), 52, False),
    ("document", ("INVOICE 2048", "TOTAL 73.50 EUR", "STATUS PAID"), 44, False),
    ("small_text", ("MODEL: PP-OCRV5", "SERIAL: OCR-8090", "DATE: 2026-08-28"), 25, False),
    ("degraded", ("LOCAL AI TEST", "QUALITY 91.7 PERCENT", "CHECK: COMPLETE"), 35, True),
)

MODELS = ("ocr-smoke", "ocr-server")
# A model executed when the gateway answered with a 2xx status.
HTTP_OK_FIRST, HTTP_OK_END = 200, 300
TEXT_KEYS = {"text", "transcription", "recognized_text", "rec_text", "rec_texts"}
CONFIDENCE_KEYS = {"confidence", "score", "rec_score", "rec_scores"}


# The fixture images: their size, where the text starts, the line spacing.
CANVAS = (1280, 420)
MARGIN_X, FIRST_LINE_Y, LINE_GAP = 72, 54, 44
NOISE_SEED, NOISE_PIXELS = 8090, 15000


def font(size: int) -> tuple[ImageFont.FreeTypeFont, str]:
    """The first of the usual Linux and macOS fonts present, and its path."""
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size), candidate
    raise RuntimeError("No supported benchmark font found")


def make_fixture(path: Path, lines: tuple[str, ...], size: int, degraded: bool) -> dict:
    """Draw one test image (noisy, rotated and blurred when `degraded`); its facts."""
    face, font_path = font(size)
    image = Image.new("RGB", CANVAS, "white")
    draw = ImageDraw.Draw(image)
    y = FIRST_LINE_Y
    for line in lines:
        draw.text((MARGIN_X, y), line, font=face, fill=(12, 18, 24))
        y += size + LINE_GAP
    if degraded:
        rng = random.Random(NOISE_SEED)
        pixels = image.load()
        for _ in range(NOISE_PIXELS):
            x, y = rng.randrange(image.width), rng.randrange(image.height)
            shade = rng.randrange(175, 246)
            pixels[x, y] = (shade, shade, shade)
        image = image.rotate(1.35, resample=Image.Resampling.BICUBIC, fillcolor="white")
        image = image.filter(ImageFilter.GaussianBlur(0.65))
        image = ImageEnhance.Contrast(image).enhance(0.82)
    image.save(path, format="PNG", optimize=False)
    data = path.read_bytes()
    return {"font": font_path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def request_ocr(base_url: str, model: str, path: Path, timeout: int) -> tuple[int, dict, float]:
    """One image through the gateway: HTTP status, answer (or error body), seconds."""
    body, content_type = form_body({"model": model, "language": "en"},
                                   ("file", path.name, path.read_bytes()))
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/images/ocr", data=body,
        headers={"Content-Type": content_type}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload, time.monotonic() - started
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw}
        return exc.code, payload, time.monotonic() - started


def collect(payload, keys: set[str]) -> list:
    """Every value under one of `keys`, anywhere in the answer, lists flattened."""
    values: list = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in keys:
                if isinstance(value, list):
                    values.extend(value)
                elif value is not None:
                    values.append(value)
            elif isinstance(value, (dict, list)):
                values.extend(collect(value, keys))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(collect(value, keys))
    return values


def normalize(text: str) -> str:
    """Upper case, runs of white space as one space."""
    return re.sub(r"\s+", " ", text.upper()).strip()


def present(value) -> bool:
    """Whether a value is text with something in it."""
    return isinstance(value, str) and bool(value.strip())


def aggregate_text(payload: dict) -> str:
    """The answer's whole-image text, under whichever key it uses; "" when none."""
    return next((payload[key] for key in ("text", "transcription", "recognized_text", "rec_text")
                 if present(payload.get(key))), "")


def line_text(lines) -> str:
    """The text of every line, joined; "" when there are none."""
    if not isinstance(lines, list):
        return ""
    return " ".join(line["text"] for line in lines
                    if isinstance(line, dict) and present(line.get("text")))


def canonical_text(payload) -> str:
    """Prefer the API's aggregate text and use line text only as fallback."""
    if isinstance(payload, dict):
        found = aggregate_text(payload) or line_text(payload.get("lines"))
        if found:
            return found
    values = [str(value) for value in collect(payload, TEXT_KEYS) if str(value).strip()]
    return " ".join(dict.fromkeys(values))


def fixtures_for(folder: Path, reuse: bool) -> dict:
    """The fixture manifest: made afresh, or the existing one, checked against the cases."""
    manifest_path = folder / "manifest.json"
    if reuse:
        manifest = json.loads(manifest_path.read_text())
        for case_id, lines, _, degraded in CASES:
            check_fixture(folder / f"{case_id}.png", manifest[case_id], lines, degraded)
        return manifest
    manifest = {}
    for case_id, lines, size, degraded in CASES:
        manifest[case_id] = {"ground_truth": " ".join(lines), "degraded": degraded,
                             **make_fixture(folder / f"{case_id}.png", lines, size, degraded)}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def check_fixture(path: Path, expected: dict, lines: tuple[str, ...], degraded: bool) -> None:
    """A reused fixture must be the one the manifest describes."""
    case_id = path.stem
    if expected["ground_truth"] != " ".join(lines):
        raise RuntimeError(f"fixture ground truth drifted: {case_id}")
    if bool(expected["degraded"]) != degraded:
        raise RuntimeError(f"fixture degradation flag drifted: {case_id}")
    if expected["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise RuntimeError(f"fixture checksum mismatch: {case_id}")


def mean(values: list[float]) -> float | None:
    """The average to six places, or None for no values."""
    return round(sum(values) / len(values), 6) if values else None


def run_case(base_url: str, model: str, image: Path, ground_truth: str,
             timeout: int) -> dict:
    """One model reading one fixture, scored against its ground truth."""
    expected = normalize(ground_truth)
    status, payload, elapsed = request_ocr(base_url, model, image, timeout)
    actual = normalize(canonical_text(payload))
    confidences = []
    for value in collect(payload, CONFIDENCE_KEYS):
        with contextlib.suppress(TypeError, ValueError):
            confidences.append(float(value))
    executed = HTTP_OK_FIRST <= status < HTTP_OK_END
    return {
        "model": model, "case": image.stem, "http_status": status,
        "model_executed": executed, "passed": executed and bool(actual),
        "duration_seconds": round(elapsed, 3), "expected": expected, "recognized": actual,
        "exact_match": actual == expected,
        "cer": round(distance(expected, actual) / max(1, len(expected)), 6),
        "mean_confidence": mean(confidences), "response": payload,
    }


def model_score(rows: list[dict]) -> dict:
    """One model's executed cases: how many, exact matches, mean CER and confidence."""
    return {
        "executed": len(rows),
        "exact_matches": sum(row["exact_match"] for row in rows),
        "mean_cer": round(sum(row["cer"] for row in rows) / max(1, len(rows)), 6),
        "mean_confidence": mean([row["mean_confidence"] for row in rows
                                 if row["mean_confidence"] is not None]),
    }


def summary(cases: list[dict]) -> dict:
    """Counts of failures, and each model's exact matches, CER and confidence."""
    scores = {model: model_score([row for row in cases
                                  if row["model"] == model and row["model_executed"]])
              for model in MODELS}
    return {
        "completed": len(cases), "total": len(MODELS) * len(CASES),
        "model_failures": sum(row["model_executed"] and not row["passed"] for row in cases),
        "infrastructure_errors": sum(not row["model_executed"] for row in cases),
        "scores": scores,
    }


def main() -> int:
    """Read every fixture with every OCR model; 1 if anything failed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help=MANAGER_HELP)
    parser.add_argument("--output", default="results/images/ocr")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--reuse-fixtures", action="store_true",
                        help="reuse and verify the existing fixture manifest")
    args = parser.parse_args()
    base_url = manager_url(args.base_url)
    output = Path(args.output)
    fixtures = output / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    manifest = fixtures_for(fixtures, args.reuse_fixtures)
    report: dict = {
        "schema_version": 1, "started_at": datetime.now(UTC).isoformat(),
        "base_url": "AI-Lab manager (address not recorded)",
        "models": list(MODELS), "cases": [],
    }
    report_path = output / "results.json"
    for model in MODELS:
        for case_id, _, _, _ in CASES:
            result = run_case(base_url, model, fixtures / f"{case_id}.png",
                              manifest[case_id]["ground_truth"], args.timeout)
            report["cases"].append(result)
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({key: result[key] for key in
                              ("model", "case", "passed", "duration_seconds", "exact_match", "cer")}))
    report["completed_at"] = datetime.now(UTC).isoformat()
    report["summary"] = summary(report["cases"])
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    failed = report["summary"]["model_failures"] or report["summary"]["infrastructure_errors"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
