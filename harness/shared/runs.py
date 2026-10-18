"""What every local generation run here records, written once.

Each speech and sound-effect runner loads one model in its own environment,
generates one file per case, and writes `raw.json`: per case the time it took,
the audio's length and real-time factor (RTF: seconds of work per second of
audio), its checksum and the memory held; per run the load time and the
platform. The model calls differ from runner to runner; this is the rest.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import platform
import resource
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

Made = TypeVar("Made")

# The seed of case 0; case N uses SEED + N, so every run draws the same audio.
SEED = 20260915
CHUNK_BYTES = 1024 * 1024
MIB = 1024 * 1024


def sha256(path: Path) -> str:
    """The file's SHA-256, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpu_memory_bytes() -> int | None:
    """Memory every process holds on the NVIDIA card, as nvidia-smi reports it."""
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=False)
    values = []
    for line in result.stdout.splitlines():
        with contextlib.suppress(ValueError):
            values.append(int(line.strip()) * MIB)
    return sum(values) if values else None


def max_rss_bytes() -> int:
    """The most memory this process has held (the kernel reports KiB on Linux)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def written_audio(destination: Path, elapsed: float, *, channels: bool = False) -> dict:
    """Facts of one file just written: time, length, RTF, sample rate, checksum."""
    import soundfile as sf

    info = sf.info(destination)
    facts = {"seconds": round(elapsed, 6), "audio_duration_s": round(info.duration, 6),
             "rtf": round(elapsed / info.duration, 6), "sample_rate": info.samplerate}
    if channels:
        facts["channels"] = info.channels
    facts["sha256"] = sha256(destination)
    return facts


def torch_facts(torch) -> dict:
    """The platform, Python, torch and CUDA versions, and the card's name."""
    return {"platform": platform.platform(), "python": platform.python_version(),
            "torch": torch.__version__, "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}


def run_cases(cases: list[dict], start: Callable[[int, dict], dict],
              generate: Callable[[int, dict], dict], *, trace: bool = False) -> list[dict]:
    """Every case once: `start` gives its record, `generate` what succeeding adds.

    A case that fails keeps its error verbatim (and its traceback with `trace`);
    the run goes on. Each record is printed as it is made.
    """
    import traceback

    records = []
    for index, case in enumerate(cases):
        record = {**start(index, case), "ok": False}
        try:
            facts = generate(index, case)
            record.update({"ok": True, **facts})
        except Exception as error:  # a benchmark records failures verbatim
            record["error"] = f"{type(error).__name__}: {error}"
            if trace:
                record["traceback"] = traceback.format_exc()
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    return records


def write_raw(out: Path, raw: dict) -> int:
    """Write `raw.json`; 0 when every case succeeded, else 1."""
    (out / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return 0 if all(case["ok"] for case in raw["cases"]) else 1


def output_folder(out: str) -> tuple[Path, Path]:
    """The run's folder and its `audio/` folder, created."""
    folder = Path(out).resolve()
    (folder / "audio").mkdir(parents=True, exist_ok=True)
    return folder, folder / "audio"


def manifest_cases(manifest: Path, limit: int | None = None) -> list[dict]:
    """The manifest's cases, the first `limit` of them when given."""
    cases = json.loads(manifest.read_text(encoding="utf-8"))["cases"]
    return cases[:limit] if limit is not None else cases


def runner_arguments(*, model: bool = True, manifest: bool = True, reference: bool = False):
    """The command line every runner starts from: --model, --manifest, --out.

    With `reference`, also the voice to clone: --reference-audio and
    --reference-text. A runner adds its own options to what this returns.
    """
    parser = argparse.ArgumentParser()
    if model:
        parser.add_argument("--model", required=True)
    if manifest:
        parser.add_argument("--manifest", required=True)
    if reference:
        parser.add_argument("--reference-audio", required=True)
        parser.add_argument("--reference-text", required=True)
    parser.add_argument("--out", required=True)
    return parser


def load_on_card(torch, build: Callable[[], Any]) -> tuple[Any, float, int]:
    """Build the model with the card's memory counters reset; (model, seconds, bytes held)."""
    import time

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = build()
    return model, time.perf_counter() - started, torch.cuda.memory_allocated()


class Runner:
    """One generation run, start to `raw.json` (Template method).

    A runner says how its model loads (`load`), what a case's record starts
    with (`start`), how one case is generated (`generate`) and what the run
    records about itself (`facts`). `main` does the rest the same way for every
    runner: the command line, the output folder, timing the load on the card,
    every case, `raw.json` and the exit code.
    """

    #: Also take --reference-audio and --reference-text (a voice to clone).
    reference = False
    #: Take --model (a checkpoint path or name).
    takes_model = True
    #: Take --manifest (the cases to run).
    takes_manifest = True
    #: Keep each failed case's traceback.
    trace = False

    def __init__(self) -> None:
        # Empty until `main` parses the command line.
        self.args = argparse.Namespace()
        self.out = self.audio_out = Path()
        self.load_s = 0.0
        # None when the model is not on the card (a server the run only calls).
        self.load_vram: int | None = 0
        # The engine's own model object and this process (psutil), set by `load`.
        # Both come from libraries with no type information, hence `Any`.
        self.model: Any = None
        self.records: list[dict] = []
        self.process: Any = None

    # -- what each runner says ------------------------------------------------

    def options(self, parser) -> None:
        """Add this runner's own command-line options."""

    def load(self):
        """The model, loaded."""
        raise NotImplementedError

    def cases(self) -> list[dict]:
        """The cases to run: the manifest's, the first `--limit` when given."""
        return manifest_cases(self.manifest_path, getattr(self.args, "limit", None))

    def start(self, _index: int, case: dict) -> dict:
        """A case's record before it runs."""
        return {"id": case["id"], "language": case["language"], "text": case["text"]}

    def generate(self, index: int, case: dict) -> dict:
        """Generate one case; what its record gains when it succeeds."""
        raise NotImplementedError

    def facts(self, records: list[dict]) -> dict:
        """What `raw.json` records about the run, beside its cases."""
        raise NotImplementedError

    # -- the same for every runner --------------------------------------------

    @property
    def model_path(self) -> Path:
        """The checkpoint given with --model."""
        return Path(self.args.model).resolve()

    @property
    def manifest_path(self) -> Path:
        """The manifest given with --manifest."""
        return Path(self.args.manifest).resolve()

    @property
    def reference_path(self) -> Path:
        """The voice to clone, given with --reference-audio."""
        return Path(self.args.reference_audio).resolve()

    def destination(self, case: dict) -> Path:
        """Where one case's audio is written."""
        return self.audio_out / f"{case['id']}.wav"

    @staticmethod
    def timed(produce: Callable[[], Made]) -> tuple[Made, float]:
        """`produce()` with the card's peak-memory counter reset first; (its result, seconds)."""
        import time

        import torch

        torch.cuda.reset_peak_memory_stats()
        before = time.perf_counter()
        result = produce()
        return result, time.perf_counter() - before

    def measured(self, destination: Path, elapsed: float, *, channels: bool = False,
                 process_rss: bool = True) -> dict:
        """A written case's facts, the card's peak memory, and this process's memory.

        `process_rss`: the memory held now (`rss_bytes`, from `self.process`), or
        the most ever held (`max_rss_bytes`).
        """
        facts = {**written_audio(destination, elapsed, channels=channels),
                 "peak_vram_bytes": peak_vram()}
        if process_rss:
            facts["rss_bytes"] = self.process.memory_info().rss
        else:
            facts["max_rss_bytes"] = max_rss_bytes()
        return facts

    @staticmethod
    def seed(index: int) -> None:
        """Seed torch on the processor and the card for case `index`."""
        import torch

        torch.manual_seed(SEED + index)
        torch.cuda.manual_seed_all(SEED + index)

    def load_timed(self) -> None:
        """Load the model on the card, timing it and the memory it takes."""
        import torch

        self.model, self.load_s, self.load_vram = load_on_card(torch, self.load)

    def main(self, argv: list[str] | None = None) -> int:
        """Parse, load, run every case, write `raw.json`; 1 if a case failed."""
        parser = runner_arguments(model=self.takes_model, manifest=self.takes_manifest,
                                  reference=self.reference)
        self.options(parser)
        self.args = parser.parse_args(argv)
        self.out, self.audio_out = output_folder(self.args.out)
        self.load_timed()
        self.records = run_cases(self.cases(), self.start, self.generate, trace=self.trace)
        return write_raw(self.out, {**self.facts(self.records), "cases": self.records})


def peak_vram() -> int:
    """The most card memory torch has held since its counter was last reset."""
    import torch

    return torch.cuda.max_memory_allocated()


def peak_of(records: list[dict], key: str = "peak_vram_bytes"):
    """The highest value of `key` over the cases, 0 when none recorded it."""
    return max((record.get(key, 0) for record in records), default=0)
