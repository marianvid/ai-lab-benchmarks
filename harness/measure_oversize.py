#!/usr/bin/env python3
"""What it costs to run a model larger than the card.

AI-Lab refuses to load a model that does not fit in VRAM, and that refusal is
deliberate: this machine's GPU hangs off an OCuLink cable, so a model split
between card and system memory sends every token across that link. The refusal
is a design decision, not a limitation — but a decision is worth more with a
number behind it.

So this measures the thing AI-Lab will not do: start llama.cpp by hand with
part of the model on the card and the rest in RAM, at several splits, and record
what each costs. Loading time, and then the speed of reading a prompt and
writing an answer.

It is the only script here that does not go through AI-Lab, and it says so.
The server listens on the port named by the setting `benchmark.oversize_port`
and logs to the scratch folder named by `benchmark.scratch_dir`, both in
AI-Lab's configuration (see `shared/lab.py`).

    python3 measure_oversize.py --model /models/gguf/.../model.gguf --out oversize.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

# The repository root, so the harness's own modules import as `harness.…`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from harness.shared.lab import LOOPBACK, setting


def port() -> int:
    """The port the hand-started llama.cpp server listens on: `benchmark.oversize_port`."""
    return int(setting("oversize_port"))


PROMPT = ("Read the following function and rewrite it to be clearer, keeping "
          "the behaviour identical.\n\n"
          "def f(a,b,c=None):\n"
          "    r=[]\n"
          "    for i in range(len(a)):\n"
          "        if c is None or a[i]>c:\n"
          "            r.append(a[i]*b)\n"
          "    return r\n")


def wait_ready(seconds: int, process: subprocess.Popen) -> float | None:
    """Seconds until the server answers, or None if it stops or gives up.

    Watching the process matters: llama.cpp exits within seconds when the model
    will not fit, and waiting the full timeout for a process that is already
    dead wastes ten minutes per attempt.
    """
    started = time.perf_counter()
    while time.perf_counter() - started < seconds:
        if process.poll() is not None:
            return None
        try:
            with urllib.request.urlopen(
                    f"http://{LOOPBACK}:{port()}/v1/models", timeout=5) as response:
                json.load(response)
            return time.perf_counter() - started
        except Exception:
            time.sleep(2)
    return None


def ask() -> dict:
    """One request, timed, so the split's cost shows up as tokens per second."""
    payload = {"model": "x", "messages": [{"role": "user", "content": PROMPT}],
               "max_tokens": 200, "temperature": 0.0}
    request = urllib.request.Request(
        f"http://{LOOPBACK}:{port()}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            answer = json.load(response)
    except Exception as error:
        return {"ok": False, "error": f"{type(error).__name__}: {error}"}
    elapsed = time.perf_counter() - started
    usage = answer.get("usage", {})
    return {"ok": True, "seconds": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "decode_tok_s": round(usage.get("completion_tokens", 0) / elapsed, 1)}


def vram_used() -> int:
    """Memory in use on the card (MiB), or -1 when nvidia-smi cannot say."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True)
    try:
        return int(result.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


# An idle card reads a few hundred MiB; below this the memory is back.
IDLE_VRAM_MB = 500
RELEASE_WAIT_S = 30


def server_command(server: str, model: str, layers: int, context: int) -> list[str]:
    """The llama-server command for one split.

    layers < 0 means: say nothing, and let llama.cpp decide the split itself.
    That is what it does well, and forcing a number makes it give up rather
    than fit — "n_gpu_layers already set by user, abort" in its own words.
    """
    command = [server, "--model", model, "--host", LOOPBACK, "--port", str(port()),
               "--ctx-size", str(context), "--flash-attn", "on", "--no-warmup"]
    return command + (["--n-gpu-layers", str(layers)] if layers >= 0 else [])


def stop(process: subprocess.Popen) -> None:
    """Stop the server, then wait for the driver to give the memory back."""
    stopping = time.perf_counter()
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=120)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=60)
    for _ in range(RELEASE_WAIT_S):
        if vram_used() < IDLE_VRAM_MB:
            break
        time.sleep(1)
    print(f"    stopped in {round(time.perf_counter()-stopping,1)}s, "
          f"VRAM now {vram_used()} MB", flush=True)


def one_split(server: str, model: str, layers: int, context: int, wait: int) -> dict:
    """Start the server with `layers` on the card, measure, stop it.

    The server's own output is kept, in the scratch folder of AI-Lab's
    configuration (`benchmark.scratch_dir`): when a split fails to load, that
    is the only place that says why.
    """
    logpath = pathlib.Path(setting("scratch_dir")) / f"llama-oversize-{layers}.log"
    logpath.parent.mkdir(parents=True, exist_ok=True)
    split = layers if layers >= 0 else "chosen by llama.cpp"
    with logpath.open("w") as logfile:
        process = subprocess.Popen(server_command(server, model, layers, context),
                                   stdout=logfile, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            ready = wait_ready(wait, process)
            if ready is None:
                logfile.flush()
                tail = [line for line in logpath.read_text(errors="replace").splitlines()
                        if line.strip()][-4:]
                return {"gpu_layers": split, "ok": False,
                        "error": ("the server stopped" if process.poll() is not None
                                  else f"did not answer within {wait}s"),
                        "server_said": tail}
            return {"gpu_layers": split, "ok": True, "load_s": round(ready, 1),
                    "vram_mb": vram_used(), "generation": ask()}
        finally:
            stop(process)


def main() -> int:
    """Measure every split asked for and write the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--server", required=True, help="path to llama-server")
    parser.add_argument("--splits", default="-1",
                        help="layer counts to try; -1 lets llama.cpp choose")
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--wait", type=int, default=1800)
    parser.add_argument("--out")
    arguments = parser.parse_args()

    size_gb = round(pathlib.Path(arguments.model).stat().st_size / 2**30, 1)
    print(f"model: {arguments.model} ({size_gb} GB)", flush=True)

    results = []
    for layers in [int(x) for x in arguments.splits.split(",")]:
        print(f"  --n-gpu-layers {layers}", flush=True)
        entry = one_split(arguments.server, arguments.model, layers, arguments.context, arguments.wait)
        print(f"    {json.dumps(entry)}", flush=True)
        results.append(entry)

    report = {"test": "oversize", "through_ai_lab": False,
              "model_path": arguments.model, "size_gb": size_gb,
              "context": arguments.context, "splits": results}
    if arguments.out:
        pathlib.Path(arguments.out).write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print(f"written to {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
