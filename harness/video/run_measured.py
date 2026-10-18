#!/usr/bin/env python3
"""Run a video benchmark command while recording wall time and resource peaks."""

from __future__ import annotations

import argparse
import contextlib
import json
import pathlib
import subprocess
import threading
import time

import psutil


def gpu_sample() -> tuple[int, int]:
    """Card memory in use (bytes) and utilisation (%), now; zeros when there is no card to ask."""
    try:
        completed = subprocess.run(
            [
                "nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                "--format=csv,noheader,nounits"
            ],
            check=False, capture_output=True, text=True
        )
    except OSError:                 # no nvidia-smi on this machine: nothing to sample
        return 0, 0
    try:
        memory, utilisation = completed.stdout.strip().split(", ", 1)
        return int(memory) * 1024 * 1024, int(utilisation)
    except (TypeError, ValueError):
        return 0, 0


def rss_tree(process: psutil.Process) -> int:
    """Memory held by a process and all its children."""
    total = 0
    try:
        processes = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0
    for item in processes:
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            total += item.memory_info().rss
    return total


SAMPLE_EVERY_S = 0.5
JOIN_TIMEOUT_S = 2


def options() -> tuple[argparse.Namespace, list[str]]:
    """The command line, and the command to run after `--`."""
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
    return args, command


class Monitor:
    """Samples the card and the process tree in the background until stopped."""

    def __init__(self, process: subprocess.Popen, started: float) -> None:
        self.process = psutil.Process(process.pid)
        self.started = started
        self.samples: list[dict] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self) -> None:
        """Take a sample every SAMPLE_EVERY_S seconds."""
        while not self.stop.wait(SAMPLE_EVERY_S):
            gpu_memory, gpu_utilisation = gpu_sample()
            self.samples.append({
                "elapsed_s": round(time.perf_counter() - self.started, 3),
                "gpu_memory_bytes": gpu_memory,
                "gpu_utilisation_percent": gpu_utilisation,
                "rss_bytes": rss_tree(self.process),
            })

    def peak(self, key: str) -> int:
        """The highest value of one sampled quantity, 0 with no samples."""
        return max((sample[key] for sample in self.samples), default=0)


def run(command: list[str], log_path: pathlib.Path) -> tuple[int, float, Monitor]:
    """Run the command to its end with its output in the log; exit code, seconds, samples."""
    with log_path.open("w", encoding="utf-8") as log:
        started = time.perf_counter()
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        monitor = Monitor(process, started)
        monitor.thread.start()
        returncode = process.wait()
        monitor.stop.set()
        monitor.thread.join(timeout=JOIN_TIMEOUT_S)
        return returncode, time.perf_counter() - started, monitor


def main() -> int:
    """Run a command, sampling its memory and the card until it ends."""
    args, command = options()
    record_path = pathlib.Path(args.record)
    log_path = pathlib.Path(args.log)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    returncode, wall_s, monitor = run(command, log_path)

    record = {
        "schema_version": 1,
        "model": args.model,
        "case": args.case,
        "status": "succeeded" if returncode == 0 else "failed",
        "returncode": returncode,
        "wall_s": round(wall_s, 3),
        "peak_gpu_memory_bytes": monitor.peak("gpu_memory_bytes"),
        "peak_gpu_utilisation_percent": monitor.peak("gpu_utilisation_percent"),
        "peak_rss_bytes": monitor.peak("rss_bytes"),
        "artifact": args.artifact,
        "log": str(log_path),
        "command": command,
        "sample_count": len(monitor.samples),
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
