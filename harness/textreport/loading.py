"""The loading page: cold and warm loads, unloads, and a model larger than the card."""

from __future__ import annotations

import pathlib

from .table import cell, header, page, tested


def intro(warm_measured: bool) -> list[str]:
    """What the loads measure: cold only, or cold and then warm."""
    lines = [
        "How long it takes to get a model onto the card and off it again.",
        "",
    ]
    if warm_measured:
        return lines + [
            "Loading is measured twice. The **first load** happens with the file",
            "not in memory, so it includes reading 4 to 22 GB from the NVMe. The",
            "**reload** happens immediately afterwards, when the operating system",
            "still holds the file in its [page cache](glossary.md#page-cache) and",
            "the disk is skipped entirely.",
            "",
            "The host's page cache was dropped before the run, so the first loads",
            "are genuinely cold.",
            "",
        ]
    return lines + [
        "**These are cold loads**: the host's page cache was dropped before",
        "the run, so each figure includes reading the weights from NVMe.",
        "",
    ]


def seconds(value) -> str:
    """A time to one place with its unit, or a dash."""
    return (cell(value, 1) + " s") if value is not None else "—"


def table(rows: list[dict]) -> list[str]:
    """Size, first load, reload and unload of every model tested."""
    lines = [
        "| Model | Engine | On disk | First load (cold) | Reload (warm) | Unload |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for entry in rows:
        size = entry.get("size_bytes")
        lines.append(
            f"| {entry['model']} | {entry['engine']} "
            f"| {(f'{size / 1024 ** 3:.1f} GB') if size else '—'} "
            f"| {seconds(entry.get('load', {}).get('load_s'))} "
            f"| {seconds((entry.get('reload') or {}).get('load_s'))} "
            f"| {cell(entry.get('unload', {}).get('unload_s'), 1)} s |")
    return lines


def findings() -> list[str]:
    """What the table shows, written after it."""
    return [
        "",
        "**Reading the weights is a small part of a vLLM start.** Its own startup",
        "log puts the disk read at 9.3 seconds out of 111. The rest is importing",
        "torch and CUDA, profiling memory, compiling kernels, and — on a",
        "multimodal model — pushing invented images and audio through the model",
        "to measure those paths. [The vLLM start sequence]"
        "(vllm-startup.md) breaks it down phase by phase.",
        "",
        "**The cold-to-warm gaps above were not isolated.** They are inconsistent",
        "across models of similar size — 95 s for one, 5 s for another — so the",
        "disk does not account for them. The likeliest cause is vLLM's",
        "compiled-kernel cache: an empty one turned a 47-second start into 241",
        "seconds in a separate measurement.",
        "",
        "**72 of those 111 seconds are avoidable on a multimodal model.** The",
        "`--language-model-only` flag skips the multimodal profiling and warm-up",
        "and takes the same model from 111 seconds to 39, at a cost of about 6%",
        "of KV cache capacity. Details and the trade-off are on the same page.",
        "",
        "**llama.cpp starts in seconds, vLLM in a minute or more.** For work that",
        "loads a model, asks one question and unloads, llama.cpp finishes before",
        "vLLM has started. Under sustained batched work the advantage reverses;",
        "the crossover is around 90 seconds.",
        "",
        "**Unloading is uniform** and set by waiting for the driver to hand the",
        "memory back, not by the model's size.",
        "",
    ]


def refused(summary: dict) -> list[str]:
    """Every model that would not start, with what it said."""
    failed = [e for e in summary.values() if not e.get("load", {}).get("ok")]
    if not failed:
        return []
    lines = ["## Would not start", "", "What the engine or the manager reported, verbatim.", ""]
    for entry in failed:
        lines.append(f"- **{entry['model']}** ({entry['engine']}): "
                     f"{entry['load'].get('error','')}")
    return lines + [""]


def oversize(summary: dict) -> list[str]:
    """The model larger than the card: its loads and what its prompts cost."""
    big = summary.get("coder-next-80b") or {}
    if not big.get("load", {}).get("ok"):
        return []
    size = big.get("size_bytes", 0) / 1024 ** 3
    runs = {r.get("test"): r for r in (big.get("latency") or {}).get("runs", [])}
    return [
        "## A model larger than the card",
        "",
        f"Qwen3-Coder-Next in GGUF Q4 is {size:.1f} GB and the card holds",
        "32.6. llama.cpp puts as many layers on the card as fit and leaves",
        "the rest in system memory, reaching them over the cable for every",
        "token. It is set per instance: -1 keeps the whole model on the card",
        "and refuses to load if it does not fit, -2 lets llama.cpp work out",
        "how many layers fit.",
        "",
        f"| | {header('Wall', 's')} |",
        "|---|---:|",
        f"| First load (cold) | {cell(big['load'].get('load_s'), 1)} s |",
        f"| Reload (warm) | {cell((big.get('reload') or {}).get('load_s'), 1)} s |",
        f"| Unload | {cell((big.get('unload') or {}).get('unload_s'), 1)} s |",
        "",
        "Per gigabyte that is the same rate as a model that fits: 0.50",
        "seconds against 0.52 for Qwen3.6-35B at 20.6 GB. Loading is reading",
        "a file, and the part that stays in system memory never has to cross",
        "the cable at all.",
        "",
        *oversize_prompts(runs),
        "**Let llama.cpp choose the split.** Given a number it will not",
        "adjust it: `n_gpu_layers already set by user to 28, abort`, followed",
        "by a failure to allocate 26 664 MiB on a 32 623 MiB card. With the",
        "setting left on -2 the flag is not passed at all, llama.cpp measures",
        "the free memory itself, and the model runs.",
    ]


def oversize_prompts(runs: dict) -> list[str]:
    """Prompt reading and generation speed of the oversized model, and what they mean."""
    if not runs:
        return []
    lines = [
        f"| Prompt | {header('TTFT')} | {header('Prefill')} "
        f"| {header('Decode')} |",
        "|---|---:|---:|---:|",
    ]
    for name in ("short prompt (~500 tok)", "medium prompt (~9k tok)",
                 "long prompt (~29k tok)"):
        run = runs.get(name)
        if not run:
            continue
        lines.append(
            f"| {run['prompt_tokens']} tokens "
            f"| {cell(run.get('ttft_s'), 2)} s "
            f"| {cell(run.get('prefill_tok_s'), 1)} "
            f"| {cell(run.get('decode_tok_s'), 1)} |")
    return lines + [
        "",
        "**Generation barely notices.** 52 to 57 tokens per second,",
        "which is in the same range as models that fit entirely. Only a",
        "small share of a mixture-of-experts model is used for any one",
        "token, so most of what sits in system memory is never read.",
        "",
        "**Prompt reading is where it hurts.** 3 043 tokens per second",
        "on a short prompt, 291 on a medium one, 466 on a long one — not",
        "a straight line, and not measured often enough to say why the",
        "long prompt beats the medium one. What matters is the size of",
        "the drop: reading a prompt processes it all at once, so every",
        "layer sitting in system memory has the whole batch sent to it",
        "and back. A 29 000-token prompt takes 53 seconds before the",
        "first word of the answer.",
        "",
        "**So it suits generation, not long prompts.** Which is the wrong",
        "way round for an agent, since an agent sends whole files.",
        "",
    ]


def loading_page(summary: dict, results: pathlib.Path, out: pathlib.Path) -> None:
    """Write `loading.md`: the load table, what it shows, failures, the oversized model."""
    rows = tested(summary)
    warm_measured = any((e.get("reload") or {}).get("load_s") for e in rows)
    lines = [*intro(warm_measured), *table(rows), *findings(), *refused(summary),
             *oversize(summary)]
    page(out / "loading.md", "Loading and unloading", lines)
