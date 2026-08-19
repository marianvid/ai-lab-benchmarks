#!/usr/bin/env python3
"""Run every benchmark against every model, unattended, and write the results.

One model at a time: load it through AI-Lab, wait until it answers, run the
tests, unload it, record how long the loading and unloading took. A single card
holds one model at a time, so this is a sequence, not a fan-out.

**It is built to survive its own failures.** A model that will not start, a test
that crashes, an engine that hangs — each is recorded and the run moves on. A
night that stops at the second model because the third was misconfigured is a
night wasted, and the whole point of running unattended is that nobody is
watching.

Everything is written as it happens. If this is killed halfway, whatever
finished is on disk and is usable.

    python3 run_all.py --out /opt/bench/results
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

MANAGER = "http://127.0.0.1:8090"
PYTHON = "/opt/bench/.venv/bin/python"
HARNESS = "/opt/bench/harness"
DATA = "/opt/bench/eval-data"

# The six models the tests run against, and one that is only weighed.
#
# The six were chosen from the August study: the ones that won something, the
# one in production, the smallest, and the weakest. A benchmark with no weak
# entry cannot show that it discriminates.
MODELS = [
    ("text-bulk",     8084, "Gemma-4-26B-A4B",     "vLLM",      "NVFP4", True),
    ("gemma26-gguf",  8086, "Gemma-4-26B-A4B",     "llama.cpp", "GGUF",  True),
    ("text-quality",  8083, "Qwopus3.6-27B-Coder", "vLLM",      "NVFP4", True),
    ("coder-fast",    8082, "Qwen3-Coder-30B-A3B", "vLLM",      "NVFP4", True),
    ("qwen-coder",    8080, "Qwen3.6-35B-A3B",     "llama.cpp", "GGUF",  True),
    ("qwen36-nvfp4",  8085, "Qwen3.6-35B-A3B",     "vLLM",      "NVFP4", True),
    ("gemma-general", 8081, "Gemma-4-E4B",         "llama.cpp", "GGUF",  True),
    ("glm-flash",     8087, "GLM-4.7-Flash",       "vLLM",      "NVFP4", True),
    # Weighed, not tested: it is here to show that a 47 GB model runs at all on
    # a 32 GB card, and what that costs in loading time.
    ("coder-next-80b", 8088, "Coder-Next 80B",     "llama.cpp", "GGUF",  False),
]

# Quality is measured once, with enough requests in flight to keep the card
# busy. The throughput curve is a separate, smaller run: the question there is
# how the engine behaves as concurrency rises, not how well it answers.
QUALITY_CONCURRENCY = 8
THROUGHPUT_CONCURRENCY = [1, 8, 32, 64]
THROUGHPUT_LANGUAGES = "en,ru,zh"      # Latin, Cyrillic, Han


def api(path: str, method: str = "GET", timeout: int = 900) -> dict:
    request = urllib.request.Request(MANAGER + path, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def wait_ready(port: int, seconds: int = 900) -> bool:
    """Loading returns when the engine says it is up; ask it something anyway."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models",
                                        timeout=10) as response:
                json.load(response)
            return True
        except Exception:
            time.sleep(3)
    return False


def load(instance: str, port: int) -> dict:
    started = time.perf_counter()
    try:
        result = api(f"/api/instances/{instance}/load", "POST")
    except Exception as error:
        return {"ok": False, "error": f"{type(error).__name__}: {error}"}
    elapsed = time.perf_counter() - started
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "load failed"),
                "load_s": round(elapsed, 1)}
    if not wait_ready(port):
        return {"ok": False, "error": "loaded but never answered",
                "load_s": round(elapsed, 1)}
    return {"ok": True, "load_s": round(elapsed, 1),
            "load_ms_reported": result.get("total_ms")}


def unload(instance: str) -> dict:
    started = time.perf_counter()
    try:
        result = api(f"/api/instances/{instance}/unload", "POST", timeout=300)
    except Exception as error:
        return {"ok": False, "error": str(error)}
    return {"ok": bool(result.get("ok")), "unload_s": round(time.perf_counter() - started, 1),
            "unload_ms_reported": result.get("total_ms")}


def bench(script: str, port: int, label: str, concurrency: int,
          extra: list[str], out: pathlib.Path, log) -> dict | None:
    """One benchmark. Never raises: a failure is a recorded fact, not a stop."""
    command = [PYTHON, f"{HARNESS}/{script}", f"http://127.0.0.1:{port}",
               label, str(concurrency), "--data", DATA, "--out", str(out), *extra]
    log(f"    {script} c={concurrency} {' '.join(extra)}")
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=14400, cwd=HARNESS,
                                   env={"BENCH_PYTHON": PYTHON, "PATH": "/usr/bin:/bin",
                                        "HOME": "/var/lib/ai-lab"})
    except subprocess.TimeoutExpired:
        log(f"      timed out after {round(time.perf_counter()-started)}s")
        return None
    if completed.returncode != 0 or not out.exists():
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        log(f"      failed: {tail[-1][:150] if tail else 'no output'}")
        return None
    log(f"      done in {round(time.perf_counter()-started)}s")
    return json.loads(out.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="/opt/bench/results")
    parser.add_argument("--only", help="comma-separated instance ids")
    parser.add_argument("--skip-throughput", action="store_true")
    arguments = parser.parse_args()

    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    logfile = (out / "run.log").open("a", encoding="utf-8")

    def log(message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        print(f"{stamp} {message}", flush=True)
        logfile.write(f"{stamp} {message}\n")
        logfile.flush()

    wanted = arguments.only.split(",") if arguments.only else None
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    log(f"=== starting: {len(MODELS)} models -> {out} ===")
    for instance, port, name, engine, fmt, full in MODELS:
        if wanted and instance not in wanted:
            continue
        log(f"--- {instance} ({name}, {engine} {fmt}) ---")
        entry = {"instance": instance, "model": name, "engine": engine,
                 "format": fmt, "tested": full}

        loaded = load(instance, port)
        entry["load"] = loaded
        if not loaded["ok"]:
            log(f"    will not start: {loaded.get('error')}")
            summary[instance] = entry
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
            continue
        log(f"    loaded in {loaded['load_s']}s")

        if full:
            entry["classification"] = bench(
                "bench_classify.py", port, instance, QUALITY_CONCURRENCY, [],
                out / f"{instance}-classify.json", log)
            entry["comprehension"] = bench(
                "bench_comprehension.py", port, instance, QUALITY_CONCURRENCY,
                ["--limit", "100"], out / f"{instance}-comprehension.json", log)
            entry["translation"] = bench(
                "bench_translate.py", port, instance, QUALITY_CONCURRENCY,
                ["--limit", "50"], out / f"{instance}-translate.json", log)
            entry["coding"] = bench(
                "bench_coding.py", port, instance, QUALITY_CONCURRENCY, [],
                out / f"{instance}-coding.json", log)

            if not arguments.skip_throughput:
                curve = {}
                for concurrency in THROUGHPUT_CONCURRENCY:
                    result = bench(
                        "bench_classify.py", port, instance, concurrency,
                        ["--languages", THROUGHPUT_LANGUAGES],
                        out / f"{instance}-throughput-c{concurrency}.json", log)
                    if result:
                        curve[str(concurrency)] = {
                            k: result[k] for k in
                            ("wall_s", "items_per_s", "prefill_tok_s", "decode_tok_s")}
                entry["throughput_curve"] = curve

        entry["unload"] = unload(instance)
        log(f"    unloaded in {entry['unload'].get('unload_s')}s")

        summary[instance] = entry
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        log(f"    written to {summary_path}")

    log("=== finished ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
