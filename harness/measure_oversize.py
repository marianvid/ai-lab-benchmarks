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

    python3 measure_oversize.py --model /models/gguf/.../model.gguf --out oversize.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import signal
import subprocess
import time
import urllib.error
import urllib.request

SERVER = "/opt/ai/llama.cpp/build/bin/llama-server"
PORT = 8099

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
                    f"http://127.0.0.1:{PORT}/v1/models", timeout=5) as response:
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
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
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
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True)
    try:
        return int(result.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


def one_split(model: str, layers: int, context: int, wait: int) -> dict:
    """Start the server with `layers` on the card, measure, stop it."""
    command = [SERVER, "--model", model, "--host", "127.0.0.1", "--port", str(PORT),
               "--ctx-size", str(context), "--flash-attn", "on", "--no-warmup"]
    # layers < 0 means: say nothing, and let llama.cpp decide the split itself.
    # That is what it does well, and forcing a number makes it give up rather
    # than fit — "n_gpu_layers already set by user, abort" in its own words.
    if layers >= 0:
        command += ["--n-gpu-layers", str(layers)]
    # Keep the server's own output. Discarding it means that when a split
    # fails to load there is nothing to say why, which is the moment you most
    # need to know.
    logpath = pathlib.Path(f"/tmp/llama-oversize-{layers}.log")
    logfile = logpath.open("w")
    started = time.perf_counter()
    process = subprocess.Popen(command, stdout=logfile, stderr=subprocess.STDOUT,
                               start_new_session=True)
    try:
        ready = wait_ready(wait, process)
        if ready is None:
            logfile.flush()
            tail = [line for line in logpath.read_text(errors="replace").splitlines()
                    if line.strip()][-4:]
            return {"gpu_layers": layers if layers >= 0 else "chosen by llama.cpp",
                    "ok": False,
                    "error": ("the server stopped" if process.poll() is not None
                              else f"did not answer within {wait}s"),
                    "server_said": tail}
        entry = {"gpu_layers": layers if layers >= 0 else "chosen by llama.cpp",
                 "ok": True,
                 "load_s": round(ready, 1), "vram_mb": vram_used()}
        entry["generation"] = ask()
        return entry
    finally:
        stopping = time.perf_counter()
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=60)
        # Give the driver a moment to actually give the memory back.
        for _ in range(30):
            if vram_used() < 500:
                break
            time.sleep(1)
        logfile.close()
        print(f"    stopped in {round(time.perf_counter()-stopping,1)}s, "
              f"VRAM now {vram_used()} MB", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
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
        entry = one_split(arguments.model, layers, arguments.context, arguments.wait)
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
