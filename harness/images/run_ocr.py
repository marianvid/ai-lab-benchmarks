#!/usr/bin/env python3
"""Run a reproducible PP-OCRv5 mobile/server comparison through AI-Lab."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


CASES = (
    ("clean", ("AI LAB BENCHMARK 2026",), 52, False),
    ("document", ("INVOICE 2048", "TOTAL 73.50 EUR", "STATUS PAID"), 44, False),
    ("small_text", ("MODEL: PP-OCRV5", "SERIAL: OCR-8090", "DATE: 2026-08-28"), 25, False),
    ("degraded", ("LOCAL AI TEST", "QUALITY 91.7 PERCENT", "CHECK: COMPLETE"), 35, True),
)

MODELS = ("ocr-smoke", "ocr-server")
TEXT_KEYS = {"text", "transcription", "recognized_text", "rec_text", "rec_texts"}
CONFIDENCE_KEYS = {"confidence", "score", "rec_score", "rec_scores"}


def font(size: int) -> tuple[ImageFont.FreeTypeFont, str]:
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
    face, font_path = font(size)
    image = Image.new("RGB", (1280, 420), "white")
    draw = ImageDraw.Draw(image)
    y = 54
    for line in lines:
        draw.text((72, y), line, font=face, fill=(12, 18, 24))
        y += size + 44
    if degraded:
        rng = random.Random(8090)
        pixels = image.load()
        for _ in range(15000):
            x, y = rng.randrange(image.width), rng.randrange(image.height)
            shade = rng.randrange(175, 246)
            pixels[x, y] = (shade, shade, shade)
        image = image.rotate(1.35, resample=Image.Resampling.BICUBIC, fillcolor="white")
        image = image.filter(ImageFilter.GaussianBlur(0.65))
        image = ImageEnhance.Contrast(image).enhance(0.82)
    image.save(path, format="PNG", optimize=False)
    data = path.read_bytes()
    return {"font": font_path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def multipart(model: str, path: Path) -> tuple[bytes, str]:
    boundary = "----ailab-ocr-" + uuid.uuid4().hex
    chunks = []
    for name, value in (("model", model), ("language", "en")):
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode()
    )
    chunks.append(path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def request_ocr(base_url: str, model: str, path: Path, timeout: int) -> tuple[int, dict, float]:
    body, boundary = multipart(model, path)
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/images/ocr",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
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
    values = []
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
    return re.sub(r"\s+", " ", text.upper()).strip()


def canonical_text(payload) -> str:
    """Prefer the API's aggregate text and use line text only as fallback."""
    if isinstance(payload, dict):
        for key in ("text", "transcription", "recognized_text", "rec_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        lines = payload.get("lines")
        if isinstance(lines, list):
            values = []
            for line in lines:
                if not isinstance(line, dict):
                    continue
                value = line.get("text")
                if isinstance(value, str) and value.strip():
                    values.append(value)
            if values:
                return " ".join(values)
    values = [str(value) for value in collect(payload, TEXT_KEYS) if str(value).strip()]
    return " ".join(dict.fromkeys(values))


def distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://192.168.50.222:8090")
    parser.add_argument("--output", default="results/images/ocr")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--reuse-fixtures", action="store_true",
                        help="reuse and verify the existing fixture manifest")
    args = parser.parse_args()

    output = Path(args.output)
    fixtures = output / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    manifest_path = fixtures / "manifest.json"
    if args.reuse_fixtures:
        manifest = json.loads(manifest_path.read_text())
        for case_id, lines, _, degraded in CASES:
            path = fixtures / f"{case_id}.png"
            data = path.read_bytes()
            expected = manifest[case_id]
            if expected["ground_truth"] != " ".join(lines):
                raise RuntimeError(f"fixture ground truth drifted: {case_id}")
            if bool(expected["degraded"]) != degraded:
                raise RuntimeError(f"fixture degradation flag drifted: {case_id}")
            if expected["sha256"] != hashlib.sha256(data).hexdigest():
                raise RuntimeError(f"fixture checksum mismatch: {case_id}")
    else:
        manifest = {}
        for case_id, lines, size, degraded in CASES:
            path = fixtures / f"{case_id}.png"
            manifest[case_id] = {
                "ground_truth": " ".join(lines),
                "degraded": degraded,
                **make_fixture(path, lines, size, degraded),
            }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "models": list(MODELS),
        "cases": [],
    }
    report_path = output / "results.json"
    model_failures = 0
    infrastructure_errors = 0
    for model in MODELS:
        for case_id, _, _, _ in CASES:
            expected = normalize(manifest[case_id]["ground_truth"])
            status, payload, elapsed = request_ocr(args.base_url, model, fixtures / f"{case_id}.png", args.timeout)
            actual = normalize(canonical_text(payload))
            confidences = []
            for value in collect(payload, CONFIDENCE_KEYS):
                try:
                    confidences.append(float(value))
                except (TypeError, ValueError):
                    pass
            executed = 200 <= status < 300
            passed = executed and bool(actual)
            model_failures += int(executed and not passed)
            infrastructure_errors += int(not executed)
            result = {
                "model": model,
                "case": case_id,
                "http_status": status,
                "model_executed": executed,
                "passed": passed,
                "duration_seconds": round(elapsed, 3),
                "expected": expected,
                "recognized": actual,
                "exact_match": actual == expected,
                "cer": round(distance(expected, actual) / max(1, len(expected)), 6),
                "mean_confidence": round(sum(confidences) / len(confidences), 6) if confidences else None,
                "response": payload,
            }
            report["cases"].append(result)
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({key: result[key] for key in ("model", "case", "passed", "duration_seconds", "exact_match", "cer")}))
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    scores = {}
    for model in MODELS:
        rows = [row for row in report["cases"] if row["model"] == model and row["model_executed"]]
        confidence = [row["mean_confidence"] for row in rows if row["mean_confidence"] is not None]
        scores[model] = {
            "executed": len(rows),
            "exact_matches": sum(row["exact_match"] for row in rows),
            "mean_cer": round(sum(row["cer"] for row in rows) / max(1, len(rows)), 6),
            "mean_confidence": round(sum(confidence) / len(confidence), 6) if confidence else None,
        }
    report["summary"] = {
        "completed": len(report["cases"]),
        "total": len(MODELS) * len(CASES),
        "model_failures": model_failures,
        "infrastructure_errors": infrastructure_errors,
        "scores": scores,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return 1 if model_failures or infrastructure_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
