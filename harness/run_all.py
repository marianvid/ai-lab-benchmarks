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

    python3 run_all.py --python <bench venv>/bin/python --data <eval-data> --out <results>
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness.shared.lab import LOOPBACK, manager_url

# The harness is the folder this file sits in; nothing else is assumed.
HARNESS = str(pathlib.Path(__file__).resolve().parent)


@dataclass(frozen=True)
class Paths:
    """Where this machine keeps the benchmark: given on the command line."""

    python: str
    data: str
    home: str

# The models the tests run against, and one that is only weighed.
#
# The first eight were chosen from the August study: the ones that won
# something, the one in production, the smallest, and the weakest. A benchmark
# with no weak entry cannot show that it discriminates. Gemma-4-31B was added
# afterwards as the only dense model on the shelf.
MODELS = [
    ("text-bulk",     8084, "Gemma-4-26B-A4B",     "vLLM",      "NVFP4", True),
    ("gemma26-gguf",  8086, "Gemma-4-26B-A4B",     "llama.cpp", "GGUF",  True),
    ("text-quality",  8083, "Qwopus3.6-27B-Coder", "vLLM",      "NVFP4", True),
    ("coder-fast",    8082, "Qwen3-Coder-30B-A3B", "vLLM",      "NVFP4", True),
    ("qwen-coder",    8080, "Qwen3.6-35B-A3B",     "llama.cpp", "GGUF",  True),
    ("qwen36-nvfp4",  8085, "Qwen3.6-35B-A3B",     "vLLM",      "NVFP4", True),
    ("gemma-general", 8081, "Gemma-4-E4B",         "llama.cpp", "GGUF",  True),
    ("glm-flash",     8087, "GLM-4.7-Flash",       "vLLM",      "NVFP4", True),
    # The only dense model here. Every one of its 31B parameters works on every
    # token, where the others use 3-4B of a much larger total. Both engines, so
    # the dense/sparse difference can be read without the engine confusing it.
    ("gemma31-gguf",  8089, "Gemma-4-31B",         "llama.cpp", "GGUF",  True),
    ("gemma31-nvfp4", 8091, "Gemma-4-31B",         "vLLM",      "NVFP4", True),
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
    """One call to the manager (found as `lab.manager_url` says)."""
    request = urllib.request.Request(manager_url() + path, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def wait_ready(port: int, seconds: int = 900) -> bool:
    """Loading returns when the engine says it is up; ask it something anyway."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://{LOOPBACK}:{port}/v1/models",
                                        timeout=10) as response:
                json.load(response)
            return True
        except Exception:
            time.sleep(3)
    return False


def model_size(instance: str) -> int | None:
    """Bytes on disk for the model this instance is configured to run."""
    try:
        wanted = next(item["model_id"] for item in api("/api/instances")
                      if item["id"] == instance)
        return next(item["size_bytes"] for item in api("/api/models")
                    if item["id"] == wanted)
    except Exception:
        return None


def load(instance: str, port: int) -> dict:
    """Load one model through the manager and wait until its engine answers; timed."""
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
    """Unload one model through the manager; timed."""
    started = time.perf_counter()
    try:
        result = api(f"/api/instances/{instance}/unload", "POST", timeout=300)
    except Exception as error:
        return {"ok": False, "error": str(error)}
    return {"ok": bool(result.get("ok")), "unload_s": round(time.perf_counter() - started, 1),
            "unload_ms_reported": result.get("total_ms")}


def options() -> argparse.Namespace:
    """The command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="results folder")
    parser.add_argument("--python", required=True,
                        help="the benchmark virtual environment's python")
    parser.add_argument("--data", required=True, help="the eval-data folder")
    parser.add_argument("--home", default=os.environ.get("HOME", ""),
                        help="HOME for the benchmark processes (caches go there)")
    parser.add_argument("--only", help="comma-separated instance ids")
    parser.add_argument("--skip-throughput", action="store_true")
    parser.add_argument("--only-new", action="store_true",
                        help="skip the quality tasks and run only the latency "
                             "and long-form measurements")
    parser.add_argument("--ladders-only", action="store_true",
                        help="run only the two concurrency ladders, leaving the "
                             "quality and latency results already on disk alone")
    parser.add_argument("--skip-reload", action="store_true",
                        help="do not measure the second, warm load")
    return parser.parse_args()


@dataclass(frozen=True)
class Model:
    """One entry of MODELS: the instance, its port, and what it runs."""

    instance: str
    port: int
    name: str
    engine: str
    fmt: str
    full: bool


@dataclass(frozen=True)
class Bench:
    """One benchmark script and how to call it.

    `positional=False` is for `bench.py`, which predates the others and takes
    the output path as a third positional argument with no concurrency at all.
    """

    script: str
    concurrency: int
    extra: tuple[str, ...] = ()
    positional: bool = True


class Night:
    """One unattended pass over the models, logging and saving as it goes."""

    def __init__(self, arguments: argparse.Namespace, logfile) -> None:
        self.arguments = arguments
        self.paths = Paths(arguments.python, arguments.data, arguments.home)
        self.out = pathlib.Path(arguments.out)
        self.logfile = logfile
        self.summary_path = self.out / "summary.json"
        self.summary = (json.loads(self.summary_path.read_text())
                        if self.summary_path.exists() else {})

    def log(self, message: str) -> None:
        """Print one stamped line and append it to run.log."""
        stamp = time.strftime("%H:%M:%S")
        print(f"{stamp} {message}", flush=True)
        self.logfile.write(f"{stamp} {message}\n")
        self.logfile.flush()

    def save(self, instance: str, entry: dict) -> None:
        """Record one model's entry and rewrite the summary."""
        self.summary[instance] = entry
        self.summary_path.write_text(json.dumps(self.summary, indent=2, ensure_ascii=False))

    def command(self, bench: Bench, model: Model, out: pathlib.Path) -> list[str]:
        """The command line that runs one benchmark against one model."""
        paths = self.paths
        start = [paths.python, f"{HARNESS}/{bench.script}", f"http://{LOOPBACK}:{model.port}",
                 model.instance]
        if not bench.positional:
            return [*start, str(out)]
        command = [*start, str(bench.concurrency), "--out", str(out), *bench.extra]
        if bench.script != "bench_longform.py":
            command += ["--data", paths.data]
        return command

    def run_bench(self, bench: Bench, model: Model, out: pathlib.Path) -> dict | None:
        """One benchmark. Never raises: a failure is a recorded fact, not a stop."""
        self.log(f"    {bench.script} c={bench.concurrency} {' '.join(bench.extra)}")
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                self.command(bench, model, out), capture_output=True, text=True,
                timeout=14400, cwd=HARNESS,
                env={"BENCH_PYTHON": self.paths.python, "PATH": "/usr/bin:/bin",
                     "HOME": self.paths.home})
        except subprocess.TimeoutExpired:
            self.log(f"      timed out after {round(time.perf_counter()-started)}s")
            return None
        if completed.returncode != 0 or not out.exists():
            tail = (completed.stderr or completed.stdout or "").strip().splitlines()
            self.log(f"      failed: {tail[-1][:150] if tail else 'no output'}")
            return None
        self.log(f"      done in {round(time.perf_counter()-started)}s")
        return json.loads(out.read_text())

    def bench(self, bench: Bench, model: Model, stem: str) -> dict | None:
        """One benchmark for this model, written to `<instance>-<stem>.json`."""
        return self.run_bench(bench, model, self.out / f"{model.instance}-{stem}.json")

    def ladder(self, script: str, model: Model, extra: tuple[str, ...], stem: str) -> dict:
        """One rung per concurrency, each on an engine that has not seen the work.

        The engine is restarted between rungs. Every rung sends the same prompts,
        and vLLM keeps what it has already read: run them back to back and the
        second rung answers from cache, which reported 60 articles read in a
        quarter of a second. Restarting throws that cache away, which is the only
        way each rung measures the same thing.
        """
        curve = {}
        for concurrency in THROUGHPUT_CONCURRENCY:
            unload(model.instance)
            again = load(model.instance, model.port)
            if not again["ok"]:
                self.log(f"    could not restart for c={concurrency}: {again.get('error')}")
                break
            result = self.bench(Bench(script, concurrency, extra), model,
                                f"{stem}-c{concurrency}")
            if result:
                curve[str(concurrency)] = {
                    k: result[k] for k in
                    ("wall_s", "items_per_s", "prefill_tok_s", "decode_tok_s")}
        return curve

    def started(self, model: Model, entry: dict) -> bool:
        """Load the model (and, unless skipped, load it again warm); False if it fails."""
        loaded = load(model.instance, model.port)
        entry["load"] = loaded
        if not loaded["ok"]:
            self.log(f"    will not start: {loaded.get('error')}")
            return False
        self.log(f"    first load {loaded['load_s']}s")
        if self.arguments.skip_reload:
            return True
        # Load a second time straight away. The weights are in the page cache
        # now, so the gap between the two numbers is the cost of reading them
        # from disk rather than of setting the model up.
        entry["unload_first"] = unload(model.instance)
        reloaded = load(model.instance, model.port)
        entry["reload"] = reloaded
        if not reloaded["ok"]:
            self.log(f"    reload failed: {reloaded.get('error')}")
            return False
        self.log(f"    reload {reloaded['load_s']}s (page cache warm)")
        return True

    def quality(self, model: Model, entry: dict) -> None:
        """The four quality tasks."""
        entry["classification"] = self.bench(
            Bench("bench_classify.py", QUALITY_CONCURRENCY), model, "classify")
        entry["comprehension"] = self.bench(
            Bench("bench_comprehension.py", QUALITY_CONCURRENCY, ("--limit", "100")),
            model, "comprehension")
        entry["translation"] = self.bench(
            Bench("bench_translate.py", QUALITY_CONCURRENCY, ("--limit", "50")),
            model, "translate")
        entry["coding"] = self.bench(
            Bench("bench_coding.py", QUALITY_CONCURRENCY), model, "coding")

    def ladders(self, model: Model, entry: dict) -> None:
        """Throughput with whole articles instead of sentences, on the same
        concurrency ladder. Prompt length is what fills the cache, so this
        is the curve that describes real bulk work."""
        entry["throughput_curve"] = self.ladder(
            "bench_classify.py", model, ("--languages", THROUGHPUT_LANGUAGES), "throughput")
        entry["longform_curve"] = self.ladder(
            "bench_longform.py", model,
            ("--articles", f"{self.paths.data}/wikipedia_articles.jsonl", "--limit", "60"),
            "longform")

    def model(self, model: Model) -> None:
        """Everything for one model, saved whether it succeeds or not."""
        instance = model.instance
        self.log(f"--- {instance} ({model.name}, {model.engine} {model.fmt}) ---")
        # Merge into whatever is already recorded for this model, so a second
        # pass that adds a measurement does not erase the first pass's results.
        entry = dict(self.summary.get(instance) or {})
        entry.update({"instance": instance, "model": model.name, "engine": model.engine,
                      "format": model.fmt, "tested": model.full})
        # The size on disk, so the loading page can put a load time next to the
        # number of gigabytes it read. Asked of AI-Lab rather than written down
        # here, because a re-quantised model changes size and nobody would
        # remember to edit a constant.
        entry["size_bytes"] = model_size(instance)
        if not self.started(model, entry):
            self.save(instance, entry)
            return
        arguments = self.arguments
        if model.full and not arguments.only_new and not arguments.ladders_only:
            self.quality(model, entry)
        if model.full and not arguments.ladders_only:
            # Prompt reading and generation at three prompt sizes, one request
            # at a time. The only place long prompts are measured.
            entry["latency"] = self.bench(Bench("bench.py", 1, positional=False), model,
                                          "latency")
        if model.full and not arguments.skip_throughput:
            self.ladders(model, entry)
        entry["unload"] = unload(instance)
        self.log(f"    unloaded in {entry['unload'].get('unload_s')}s")
        self.save(instance, entry)
        self.log(f"    written to {self.summary_path}")


def main() -> int:
    """Run every test against every model, one model at a time, recording everything."""
    arguments = options()
    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = arguments.only.split(",") if arguments.only else None
    with (out / "run.log").open("a", encoding="utf-8") as logfile:
        night = Night(arguments, logfile)
        night.log(f"=== starting: {len(MODELS)} models -> {out} ===")
        for row in MODELS:
            model = Model(*row)
            if wanted and model.instance not in wanted:
                continue
            night.model(model)
        night.log("=== finished ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
