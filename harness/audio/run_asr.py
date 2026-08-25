#!/usr/bin/env python3
"""Run the Romanian ASR study through AI-Lab and preserve every outcome."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time
import unicodedata
import urllib.error
import urllib.request
import uuid


MODELS = [
    ("whisper-large-v3", "Whisper large-v3", "vLLM", "Safetensors"),
    ("whisper-large-v3-turbo", "Whisper large-v3-turbo", "vLLM", "Safetensors"),
    ("qwen3-asr-06b", "Qwen3-ASR-0.6B", "vLLM", "Safetensors"),
    ("qwen3-asr-17b", "Qwen3-ASR-1.7B", "vLLM", "Safetensors"),
    ("parakeet-tdt-06b-v3", "Parakeet TDT 0.6B v3", "NeMo", ".nemo"),
    ("canary-1b-v2", "Canary 1B v2", "NeMo", ".nemo"),
    ("nemotron-35-asr-streaming-06b", "Nemotron 3.5 ASR Streaming 0.6B", "NeMo", ".nemo"),
]


def api(base: str, path: str, method: str = "GET", timeout: int = 1200) -> object:
    request = urllib.request.Request(base + path, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def unload_running(base: str) -> list[dict]:
    outcomes = []
    for item in api(base, "/api/instances"):
        if item.get("running"):
            try:
                result = api(base, f"/api/instances/{item['id']}/unload", "POST", 300)
                outcomes.append({"instance": item["id"], "ok": bool(result.get("ok"))})
            except Exception as error:
                outcomes.append({"instance": item["id"], "ok": False, "error": str(error)})
    return outcomes


def multipart(url: str, fields: dict[str, str], filename: str,
              payload: bytes, timeout: int = 1800) -> dict:
    boundary = "ai-lab-benchmark-" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode(), b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: audio/wav\r\n\r\n", payload, b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    request = urllib.request.Request(
        url, data=b"".join(chunks), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def normalized(text: str, strip_diacritics: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    if strip_diacritics:
        text = "".join(char for char in unicodedata.normalize("NFD", text)
                       if unicodedata.category(char) != "Mn")
    text = "".join(" " if unicodedata.category(char)[0] in {"P", "S"} else char
                   for char in text)
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


def error_counts(reference: str, hypothesis: str, ascii_only: bool = False) -> tuple[int, int, int, int]:
    ref = normalized(reference, ascii_only)
    hyp = normalized(hypothesis, ascii_only)
    ref_words, hyp_words = ref.split(), hyp.split()
    return (distance(ref_words, hyp_words), len(ref_words),
            distance(list(ref), list(hyp)), len(ref))


def read_error(error: Exception) -> str:
    if isinstance(error, urllib.error.HTTPError):
        try:
            return error.read().decode("utf-8", errors="replace")
        except Exception:
            pass
    return f"{type(error).__name__}: {error}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", default="http://192.168.50.222:8090")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", help="comma-separated instance ids")
    args = parser.parse_args()

    data = pathlib.Path(args.data)
    manifest = json.loads((data / "MANIFEST.json").read_text(encoding="utf-8"))
    out = pathlib.Path(args.out)
    details_dir = out / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    wanted = set(args.only.split(",")) if args.only else None

    for instance, label, engine, weight_format in MODELS:
        if wanted and instance not in wanted:
            continue
        print(f"--- {instance}: {label} ---", flush=True)
        entry = {
            "instance": instance, "model": label, "engine": engine,
            "format": weight_format, "dataset": "google/fleurs ro_ro test",
            "selected_rows": len(manifest["items"]),
            "audio_duration_s": manifest["audio_duration_s"],
        }
        entry["preload_unloads"] = unload_running(args.manager)
        started = time.perf_counter()
        try:
            loaded = api(args.manager, f"/api/instances/{instance}/load", "POST")
            entry["load"] = {"ok": bool(loaded.get("ok")),
                             "wall_s": round(time.perf_counter() - started, 3),
                             "manager_total_ms": loaded.get("total_ms")}
            if not loaded.get("ok"):
                entry["load"]["error"] = loaded.get("error", "load failed")
                raise RuntimeError(entry["load"]["error"])
        except Exception as error:
            entry.setdefault("load", {"ok": False,
                                      "wall_s": round(time.perf_counter() - started, 3)})
            entry["load"]["error"] = read_error(error)
            summary[instance] = entry
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
            continue

        # Exercise decoder setup and kernels once, exactly as the text study
        # does. The warm-up is recorded but never scored or timed into RTF.
        warmup_item = manifest["items"][0]
        warmup_audio = data / warmup_item["path"]
        warmup_started = time.perf_counter()
        try:
            multipart(args.manager + "/v1/audio/transcriptions",
                      {"model": instance, "language": "ro"}, warmup_audio.name,
                      warmup_audio.read_bytes())
            entry["warmup"] = {"ok": True,
                               "wall_s": round(time.perf_counter() - warmup_started, 6)}
        except Exception as error:
            entry["warmup"] = {"ok": False,
                               "wall_s": round(time.perf_counter() - warmup_started, 6),
                               "error": read_error(error)}

        if not entry["warmup"]["ok"]:
            entry.update({"status": "warmup_failed", "requests": 0,
                          "successful": 0, "failed": 0, "inference_s": 0.0,
                          "real_time_factor": None,
                          "audio_seconds_per_second": None,
                          "wer": None, "cer": None,
                          "wer_without_diacritics": None,
                          "cer_without_diacritics": None})
            (details_dir / f"{instance}.json").write_text(
                json.dumps({"schema_version": 1, "instance": instance,
                            "status": "warmup_failed", "items": []},
                           ensure_ascii=False, indent=2) + "\n")
            try:
                api(args.manager, f"/api/instances/{instance}/unload", "POST", 300)
            except Exception as error:
                entry["unload"] = {"ok": False, "error": read_error(error)}
            summary[instance] = entry
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
            print(f"  warm-up FAILED: {entry['warmup']['error']}", flush=True)
            continue

        results = []
        total_inference = 0.0
        totals = {"word_errors": 0, "words": 0, "char_errors": 0, "chars": 0,
                  "ascii_word_errors": 0, "ascii_words": 0,
                  "ascii_char_errors": 0, "ascii_chars": 0}
        for position, item in enumerate(manifest["items"]):
            audio = data / item["path"]
            request_started = time.perf_counter()
            record = {"ordinal": item["ordinal"], "id": item["id"],
                      "source_row": item["source_row"],
                      "duration_s": item["duration_s"]}
            try:
                response = multipart(
                    args.manager + "/v1/audio/transcriptions",
                    {"model": instance, "language": "ro"}, audio.name,
                    audio.read_bytes())
                elapsed = time.perf_counter() - request_started
                hypothesis = str(response.get("text") or "")
                record.update({"ok": True, "inference_s": round(elapsed, 6)})
                total_inference += elapsed
                we, words, ce, chars = error_counts(item["reference"], hypothesis)
                awe, awords, ace, achars = error_counts(item["reference"], hypothesis, True)
                for key, value in (("word_errors", we), ("words", words),
                                   ("char_errors", ce), ("chars", chars),
                                   ("ascii_word_errors", awe), ("ascii_words", awords),
                                   ("ascii_char_errors", ace), ("ascii_chars", achars)):
                    totals[key] += value
                record.update({"word_errors": we, "reference_words": words,
                               "char_errors": ce, "reference_chars": chars})
            except Exception as error:
                record.update({"ok": False, "error": read_error(error),
                               "inference_s": round(time.perf_counter() - request_started, 6)})
            results.append(record)
            (details_dir / f"{instance}.json").write_text(
                json.dumps({"schema_version": 1, "instance": instance,
                            "items": results}, ensure_ascii=False, indent=2) + "\n")
            print(f"  {position + 1}/{len(manifest['items'])} {'ok' if record['ok'] else 'FAILED'}",
                  flush=True)

        successful = sum(bool(item["ok"]) for item in results)
        entry.update({
            "requests": len(results), "successful": successful,
            "failed": len(results) - successful,
            "inference_s": round(total_inference, 3),
            "real_time_factor": round(total_inference / manifest["audio_duration_s"], 4),
            "audio_seconds_per_second": round(manifest["audio_duration_s"] / total_inference, 3)
                if total_inference else None,
            "wer": round(totals["word_errors"] / totals["words"], 6) if totals["words"] else None,
            "cer": round(totals["char_errors"] / totals["chars"], 6) if totals["chars"] else None,
            "wer_without_diacritics": round(totals["ascii_word_errors"] / totals["ascii_words"], 6)
                if totals["ascii_words"] else None,
            "cer_without_diacritics": round(totals["ascii_char_errors"] / totals["ascii_chars"], 6)
                if totals["ascii_chars"] else None,
            "error_totals": totals,
        })
        unload_started = time.perf_counter()
        try:
            unloaded = api(args.manager, f"/api/instances/{instance}/unload", "POST", 300)
            entry["unload"] = {"ok": bool(unloaded.get("ok")),
                               "wall_s": round(time.perf_counter() - unload_started, 3),
                               "manager_total_ms": unloaded.get("total_ms")}
        except Exception as error:
            entry["unload"] = {"ok": False, "error": read_error(error)}
        summary[instance] = entry
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        print(f"  WER={entry['wer']} RTF={entry['real_time_factor']}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
