#!/usr/bin/env python3
"""Score generated TTS audio through one deployed AI-Lab ASR evaluator."""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def api(base: str, path: str, method: str = "GET", timeout: int = 1200) -> object:
    request = urllib.request.Request(base + path, data=b"{}" if method == "POST" else None,
                                     method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def multipart(url: str, fields: dict[str, str], path: Path) -> dict:
    boundary = "ai-lab-tts-" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([f"--{boundary}\r\n".encode(),
                       f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                       value.encode(), b"\r\n"])
    chunks.extend([f"--{boundary}\r\n".encode(),
                   f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
                   b"Content-Type: audio/wav\r\n\r\n", path.read_bytes(), b"\r\n",
                   f"--{boundary}--\r\n".encode()])
    request = urllib.request.Request(url, data=b"".join(chunks), method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=1800) as response:
        return json.load(response)


def normalized(text: str, strip_diacritics: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    if strip_diacritics:
        text = "".join(c for c in unicodedata.normalize("NFD", text)
                       if unicodedata.category(c) != "Mn")
    text = "".join(" " if unicodedata.category(c)[0] in {"P", "S"} else c for c in text)
    return re.sub(r"\s+", " ", text).strip()


def distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def counts(reference: str, hypothesis: str, strip_diacritics: bool = False) -> tuple[int, int, int, int]:
    ref = normalized(reference, strip_diacritics)
    hyp = normalized(hypothesis, strip_diacritics)
    return distance(ref.split(), hyp.split()), len(ref.split()), distance(list(ref), list(hyp)), len(ref)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", default="http://127.0.0.1:8090")
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--language", required=True, choices=("ro", "en"))
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--out", help="Optional explicit destination JSON path")
    args = parser.parse_args()
    loaded = api(args.manager, f"/api/instances/{args.evaluator}/load", "POST")
    output = {"schema_version": 1, "evaluator": args.evaluator,
              "language": args.language, "load": loaded, "models": {}}
    try:
        for name in args.result:
            root = Path(name).resolve()
            raw = json.loads((root / "raw.json").read_text(encoding="utf-8"))
            records = []
            aggregate = [0, 0, 0, 0]
            aggregate_ascii = [0, 0, 0, 0]
            by_mode: dict[str, list[int]] = {}
            by_mode_ascii: dict[str, list[int]] = {}
            language_aliases = {"en": {"en", "English"}, "ro": {"ro", "Romanian"}}
            for case in raw["cases"]:
                if not case.get("ok") or case["language"] not in language_aliases[args.language]:
                    continue
                audio = root / "audio" / f"{case['id']}.wav"
                started = time.perf_counter()
                try:
                    response = multipart(args.manager + "/v1/audio/transcriptions",
                                         {"model": args.evaluator, "language": args.language}, audio)
                    hypothesis = response.get("text", "")
                    reference = case.get("expected_text", case["text"])
                    score = counts(reference, hypothesis)
                    score_ascii = counts(reference, hypothesis, True)
                    aggregate = [a + b for a, b in zip(aggregate, score)]
                    aggregate_ascii = [a + b for a, b in zip(aggregate_ascii, score_ascii)]
                    mode = case.get("mode", "default")
                    by_mode[mode] = [a + b for a, b in zip(by_mode.get(mode, [0, 0, 0, 0]), score)]
                    by_mode_ascii[mode] = [a + b for a, b in zip(
                        by_mode_ascii.get(mode, [0, 0, 0, 0]), score_ascii)]
                    record = {"id": case["id"], "reference": reference,
                              "hypothesis": hypothesis, "seconds": round(time.perf_counter() - started, 6),
                              "mode": mode,
                              "word_errors": score[0], "reference_words": score[1],
                              "character_errors": score[2], "reference_characters": score[3]}
                    for key in ("speaker", "gender"):
                        if key in case:
                            record[key] = case[key]
                except Exception as error:
                    record = {"id": case["id"], "error": f"{type(error).__name__}: {error}"}
                records.append(record)
                print(json.dumps({"model": root.name, **record}, ensure_ascii=False), flush=True)
            groups = {}
            for key in ("gender", "speaker"):
                values = sorted({record[key] for record in records if key in record})
                if values:
                    groups[f"by_{key}"] = {}
                    for value in values:
                        rows = [record for record in records if record.get(key) == value
                                and "word_errors" in record]
                        word_errors = sum(row["word_errors"] for row in rows)
                        words = sum(row["reference_words"] for row in rows)
                        character_errors = sum(row["character_errors"] for row in rows)
                        characters = sum(row["reference_characters"] for row in rows)
                        groups[f"by_{key}"][value] = {
                            "wer": word_errors / words if words else None,
                            "cer": character_errors / characters if characters else None,
                            "completed": len(rows),
                        }
            summary = {"wer": aggregate[0] / aggregate[1] if aggregate[1] else None,
                       "cer": aggregate[2] / aggregate[3] if aggregate[3] else None,
                       "wer_without_diacritics": aggregate_ascii[0] / aggregate_ascii[1]
                       if aggregate_ascii[1] else None, "completed": len(records),
                       "by_mode": {
                           mode: {"wer": values[0] / values[1] if values[1] else None,
                                  "cer": values[2] / values[3] if values[3] else None,
                                  "wer_without_diacritics": by_mode_ascii[mode][0] / by_mode_ascii[mode][1]
                                  if by_mode_ascii[mode][1] else None}
                           for mode, values in by_mode.items()
                       }, **groups, "cases": records}
            output["models"][root.name] = summary
        print(json.dumps({name: {k: v for k, v in value.items() if k != "cases"}
                          for name, value in output["models"].items()}, indent=2), flush=True)
    finally:
        output["unload"] = api(args.manager, f"/api/instances/{args.evaluator}/unload", "POST", 300)
    destination = (Path(args.out).resolve() if args.out else
                   Path(args.result[0]).resolve().parent /
                   f"asr-{args.evaluator}-{args.language}.json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
