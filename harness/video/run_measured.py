#!/usr/bin/env python3
"""Run a video benchmark command while recording wall time and resource peaks."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import threading
import time

import psutil


def gpu_sample() -> tuple[int, int]:
    completed = subprocess.run(
        [
            "nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
            "--format=csv,noheader,nounits"
        ],
        check=False, capture_output=True, text=True
    )
    try:
        memory, utilisation = completed.stdout.strip().split(", ", 1)
        return int(memory) * 1024 * 1024, int(utilisation)
    except (TypeError, ValueError):
        return 0, 0


def rss_tree(process: psutil.Process) -> int:
    total = 0
    try:
        processes = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0
    for item in processes:
        try:
            total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--artifact")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")

    record_path = pathlib.Path(args.record)
    log_path = pathlib.Path(args.log)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    samples: list[dict] = []

    with log_path.open("w", encoding="utf-8") as log:
        started = time.perf_counter()
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        ps_process = psutil.Process(process.pid)

        def sample() -> None:
            while not stop.wait(0.5):
                gpu_memory, gpu_utilisation = gpu_sample()
                samples.append({
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "gpu_memory_bytes": gpu_memory,
                    "gpu_utilisation_percent": gpu_utilisation,
                    "rss_bytes": rss_tree(ps_process),
                })

        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        returncode = process.wait()
        stop.set()
        monitor.join(timeout=2)
        wall_s = time.perf_counter() - started

    record = {
        "schema_version": 1,
        "model": args.model,
        "case": args.case,
        "status": "succeeded" if returncode == 0 else "failed",
        "returncode": returncode,
        "wall_s": round(wall_s, 3),
        "peak_gpu_memory_bytes": max(
            (sample["gpu_memory_bytes"] for sample in samples), default=0
        ),
        "peak_gpu_utilisation_percent": max(
            (sample["gpu_utilisation_percent"] for sample in samples), default=0
        ),
        "peak_rss_bytes": max(
            (sample["rss_bytes"] for sample in samples), default=0
        ),
        "artifact": args.artifact,
        "log": str(log_path),
        "command": command,
        "sample_count": len(samples),
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
