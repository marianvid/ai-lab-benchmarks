# Loading and unloading

How long it takes to get a model onto the card and off it again.

Loading is measured twice. The **first load** happens with the file
not in memory, so it includes reading 4 to 22 GB from the NVMe. The
**reload** happens immediately afterwards, when the operating system
still holds the file in its [page cache](glossary.md#page-cache) and
the disk is skipped entirely.

The host's page cache was dropped before the run, so the first loads
are genuinely cold.

| Model | Engine | First load (cold) | Reload (warm) | Unload |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 91.6 s | 40.2 s | 2.0 s |
| Gemma-4-26B-A4B | llama.cpp | 9.0 s | 5.0 s | 2.3 s |
| Gemma-4-26B-A4B | vLLM | 212.4 s | 117.4 s | 2.3 s |
| Gemma-4-E4B | llama.cpp | 3.9 s | 2.5 s | 1.8 s |
| Qwen3-Coder-30B-A3B | vLLM | 42.1 s | 37.2 s | 2.0 s |
| Qwen3.6-35B-A3B | llama.cpp | 10.8 s | 5.3 s | 2.2 s |
| Qwen3.6-35B-A3B | vLLM | 177.0 s | 92.2 s | 2.2 s |
| Qwopus3.6-27B-Coder | vLLM | 163.4 s | 69.1 s | 2.2 s |

**Reading the weights is a small part of a vLLM start.** Its own startup
log puts the disk read at 9.3 seconds out of 111. The rest is importing
torch and CUDA, profiling memory, compiling kernels, and — on a
multimodal model — pushing invented images and audio through the model
to measure those paths. [Why vLLM takes minutes to start](vllm-startup.md) breaks it down phase by phase.

**The cold-to-warm gaps above were not isolated.** They are inconsistent
across models of similar size — 95 s for one, 5 s for another — so the
disk does not account for them. The likeliest cause is vLLM's
compiled-kernel cache: an empty one turned a 47-second start into 241
seconds in a separate measurement.

**72 of those 111 seconds are avoidable on a multimodal model.** The
`--language-model-only` flag skips the multimodal profiling and warm-up
and takes the same model from 111 seconds to 39, at a cost of about 6%
of KV cache capacity. Details and the trade-off are on the same page.

**llama.cpp starts in seconds, vLLM in a minute or more.** For work that
loads a model, asks one question and unloads, llama.cpp finishes before
vLLM has started. Under sustained batched work the advantage reverses;
the crossover is around 90 seconds.

**Unloading is uniform** and set by waiting for the driver to hand the
memory back, not by the model's size.

## Refused

AI-Lab checks free VRAM before starting an engine and declines
rather than letting the engine fail partway through.

- **Coder-Next 80B** (llama.cpp): Qwen3-Coder-Next-UD-Q4_K_XL needs about 46.2 GB but only 31.9 GB is free on the card. Unload another model, or choose a smaller one.

## A model larger than VRAM

`Qwen3-Coder-Next-UD-Q4_K_XL.gguf` is 46.2 GB; the card has 32 GB. llama.cpp can keep
part of a model on the card and the rest in system memory, moving
data across the PCIe link for every token.

AI-Lab refuses this arrangement, so llama.cpp was started directly.

| Split | Loaded | VRAM used | Generation |
|---|---:|---:|---:|
| chosen by llama.cpp | 10.5 s | 30728 MB | 42.0 tok/s |

**Let the engine choose the split.** Given a fixed `--n-gpu-layers`,
llama.cpp will not adjust a figure the user supplied: it reports
`n_gpu_layers already set by user to 36, abort` and then fails
trying to allocate 34 406 MiB on a 32 623 MiB card. With the flag
left off it works out the division itself and the model runs.

**This load time is warm.** The file had been read by earlier
attempts. A cold read of 46 GB from NVMe is considerably slower.

**Why AI-Lab refuses it.** The GPU is attached over
[OCuLink](glossary.md#oculink) at about 8 GB/s, so a split model
sends data across a cable for every token. It works for llama.cpp,
which moves computation to the data; it does not for vLLM, which
moves the data. See [Configuration](machine.md).

**The cost is not evenly spread.** Measured across four sizes of the
same model, prompt reading falls 9.5× as layers move off the card
while generation falls only 2×, and 60% of the prompt-reading loss
happens at the very first layers evicted. See
[What partial offload costs](partial-offload.md).
