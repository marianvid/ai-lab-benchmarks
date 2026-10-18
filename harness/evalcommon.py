#!/usr/bin/env python3
"""What every benchmark here needs: talk to the server, run many at once, time it.

The four benchmarks differ in what they ask and how they mark the answer. They
do not differ in how they reach the engine, how they hide a reasoning model's
scratch work, how they run requests concurrently, or how they report. That is
all here, so a fix to any of it is a fix everywhere.

**Every benchmark reports correctness and speed from the same run.** That is
the point of this study: the question is not which model is cleverest, it is
how this machine behaves under a given kind of work. A score without a duration
answers half the question.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT_S = 1800

# Reasoning models write their scratch work into the answer. It is not the
# answer, and counting it as one marks a correct model wrong.
THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    """The answer without a reasoning model's `<think>` scratch work."""
    text = THINK_RE.sub("", text or "")
    if "</think>" in text:            # an opening tag that was cut off
        text = text.split("</think>", 1)[1]
    return text.strip()


def post_json(url: str, payload: dict) -> dict:
    """Ask with thinking switched off; ask again plainly if that is rejected.

    Not every engine and model accepts `chat_template_kwargs`, and the ones
    that do not answer 400. Retrying without it is the difference between a
    benchmark that covers every model and one that quietly skips some.
    """
    with_flag = dict(payload)
    with_flag["chat_template_kwargs"] = {"enable_thinking": False}
    for attempt in (with_flag, payload):
        request = urllib.request.Request(
            url, data=json.dumps(attempt).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (400, 422) and attempt is with_flag:
                continue
            raise
    raise RuntimeError("both attempts failed")


def model_name(base: str) -> str:
    """The id of the model the server at `base` answers with."""
    with urllib.request.urlopen(base + "/v1/models", timeout=60) as response:
        return json.load(response)["data"][0]["id"]


class Run:
    """One measured pass: sends the work, counts the tokens, times the wall clock."""

    def __init__(self, base: str, model: str, concurrency: int) -> None:
        self.base = base
        self.model = model
        self.concurrency = concurrency
        self._lock = threading.Lock()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.requests = 0
        self.failed = 0
        self.wall_s = 0.0

    def ask(self, messages: list[dict], max_tokens: int,
            temperature: float = 0.0) -> str | None:
        """One chat request. Returns the answer with any scratch work removed."""
        payload = {"model": self.model, "messages": messages,
                   "max_tokens": max_tokens, "temperature": temperature}
        try:
            answer = post_json(self.base + "/v1/chat/completions", payload)
        except Exception:
            with self._lock:
                self.failed += 1
            return None
        usage = answer.get("usage", {})
        with self._lock:
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            self.requests += 1
        return strip_think(answer["choices"][0]["message"]["content"] or "")

    def _warm_up(self) -> None:
        """Exercise the engine on text that is not part of the measurement."""
        filler = ("Warm-up. " * 200) + "\n\nReply with the single word: ready."
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            list(pool.map(
                lambda _: self.ask([{"role": "user", "content": filler}],
                                   max_tokens=4),
                range(self.concurrency)))

    def reset(self) -> None:
        """Zero the token and request counters."""
        with self._lock:
            self.prompt_tokens = self.completion_tokens = 0
            self.requests = self.failed = 0

    def go(self, work: list, do, warm: bool = True) -> list:
        """Run `do` over `work`, `concurrency` at a time, and time it.

        A warm-up pass runs first and is thrown away. The first pass after a
        server starts runs about 40% slow while the engine's kernel autotuning
        settles, and a benchmark that measures that is measuring the wrong
        thing.

        The warm-up sends a prompt of its own, never one from `work`. It used
        to send the first `concurrency` items, which at 64 was the whole set of
        60 articles — so the measured pass asked for exactly what the engine
        had just read, and vLLM answered from its prefix cache. That reported
        60 articles read in a quarter of a second.
        """
        if warm and work:
            self._warm_up()
            self.reset()

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            results = list(pool.map(do, work))
        self.wall_s = time.perf_counter() - started
        return results

    def speed(self, items: int) -> dict:
        """The half of every result that is about the machine, not the model."""
        wall = self.wall_s or 1e-9
        return {
            "wall_s": round(self.wall_s, 2),
            "requests": self.requests,
            "failed_requests": self.failed,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "prefill_tok_s": round(self.prompt_tokens / wall, 1),
            "decode_tok_s": round(self.completion_tokens / wall, 1),
            "items_per_s": round(items / wall, 2),
        }


def arguments_parser(doc: str | None, *, data: bool = True,
                     languages: bool = True) -> argparse.ArgumentParser:
    """The arguments every benchmark takes: server, label, concurrency, output."""
    parser = argparse.ArgumentParser(description=doc)
    parser.add_argument("base")
    parser.add_argument("label")
    parser.add_argument("concurrency", type=int)
    if data:
        parser.add_argument("--data", default="./eval-data")
    if languages:
        parser.add_argument("--languages")
    parser.add_argument("--out")
    return parser


def language_list(text: str | None) -> list[str] | None:
    """The `--languages` value as a list, or None for every language."""
    return [code.strip() for code in text.split(",")] if text else None


def nothing_found(what: str) -> int:
    """Say the data is missing and return the exit code for it."""
    print(f"no {what} found — run get_datasets.py first", file=sys.stderr)
    return 2


def banner(label: str, model: str, *parts: str) -> None:
    """The line that opens every benchmark's output."""
    print(" | ".join([f"\n=== {label}", model, *parts]) + " ===", flush=True)


def report(path: str | None, result: dict) -> None:
    """Print the result and, when `path` is given, write it there too."""
    print(json.dumps(result, ensure_ascii=False, indent=1), flush=True)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)


def f1_scores(counts: dict) -> dict:
    """Precision, recall, F1 and accuracy from a confusion count.

    F1 rather than accuracy because these sets are deliberately unbalanced: on a
    set where one answer in seven is yes, a model that always says no scores 86%
    accuracy and is worthless.
    """
    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    total = tp + fp + tn + fn
    scores = {"n": total, "positives": tp + fn,
              "accuracy": round((tp + tn) / total, 4) if total else None}

    # With nothing to find, F1 is undefined. Reporting 0.0 there says the model
    # failed when in fact it was never asked anything, and a mean taken over
    # such zeros is worse than no mean at all.
    if tp + fn == 0:
        scores.update({"precision": None, "recall": None, "f1": None,
                       "note": "no positives in this slice, so F1 is undefined"})
        return scores

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    scores.update({"precision": round(precision, 4),
                   "recall": round(recall, 4),
                   "f1": round(f1, 4)})
    return scores
