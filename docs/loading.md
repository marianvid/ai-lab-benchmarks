# Loading and unloading

How long it takes to get a model onto the card and off it again.

Loading is measured twice. The **first load** happens with the file
not in memory, so it includes reading 4 to 22 GB from the NVMe. The
**reload** happens immediately afterwards, when the operating system
still holds the file in its [page cache](glossary.md#page-cache) and
the disk is skipped entirely.

The host's page cache was dropped before the run, so the first loads
are genuinely cold.

| Model | Engine | On disk | First load (cold) | Reload (warm) | Unload |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 19.8 GB | 91.6 s | 40.2 s | 2.0 s |
| Gemma-4-26B-A4B | llama.cpp | 15.8 GB | 9.0 s | 5.0 s | 2.3 s |
| Gemma-4-26B-A4B | vLLM | 17.5 GB | 212.4 s | 117.4 s | 2.3 s |
| Gemma-4-31B | llama.cpp | 17.5 GB | 10.2 s | 5.5 s | 2.8 s |
| Gemma-4-31B | vLLM | 21.7 GB | 40.7 s | 34.4 s | 2.1 s |
| Gemma-4-E4B | llama.cpp | 4.3 GB | 3.9 s | 2.5 s | 1.8 s |
| Qwen3-Coder-30B-A3B | vLLM | 16.9 GB | 42.1 s | 37.2 s | 2.0 s |
| Qwen3.6-35B-A3B | llama.cpp | 20.6 GB | 10.8 s | 5.3 s | 2.2 s |
| Qwen3.6-35B-A3B | vLLM | 21.8 GB | 177.0 s | 92.2 s | 2.2 s |
| Qwopus3.6-27B-Coder | vLLM | 19.2 GB | 163.4 s | 69.1 s | 2.2 s |

**Reading the weights is a small part of a vLLM start.** Its own startup
log puts the disk read at 9.3 seconds out of 111. The rest is importing
torch and CUDA, profiling memory, compiling kernels, and — on a
multimodal model — pushing dummy images and audio through the model
to measure those paths. [The vLLM start sequence](vllm-startup.md) breaks it down phase by phase.

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

## A model larger than the card

Qwen3-Coder-Next in GGUF Q4 is 46.2 GB and the card holds
32.6. llama.cpp puts as many layers on the card as fit and leaves
the rest in system memory, reaching them over the cable for every
token. It is set per instance: -1 keeps the whole model on the card
and refuses to load if it does not fit, -2 lets llama.cpp work out
how many layers fit.

| | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---:|
| First load (cold) | 22.9 s |
| Reload (warm) | 10.0 s |
| Unload | 1.9 s |

Per gigabyte that is the same rate as a model that fits: 0.50
seconds against 0.52 for Qwen3.6-35B at 20.6 GB. Loading is reading
a file, and the part that stays in system memory never has to cross
the cable at all.

| Prompt | [TTFT](glossary.md#ttft "time to first token, seconds") | [Prefill](glossary.md#prefill "prompt reading, tokens per second") | [Decode](glossary.md#decode "answer generation, tokens per second") |
|---|---:|---:|---:|
| 309 tokens | 0.10 s | 3042.7 | 56.9 |
| 7841 tokens | 26.98 s | 290.7 | 53.8 |
| 24831 tokens | 53.32 s | 465.7 | 52.1 |

**Generation barely notices.** 52 to 57 tokens per second,
which is in the same range as models that fit entirely. Only a
small share of a mixture-of-experts model is used for any one
token, so most of what sits in system memory is never read.

**Prompt reading is where it hurts.** 3 043 tokens per second
on a short prompt, 291 on a medium one, 466 on a long one — not
a straight line, and not measured often enough to say why the
long prompt beats the medium one. What matters is the size of
the drop: reading a prompt processes it all at once, so every
layer sitting in system memory has the whole batch sent to it
and back. A 29 000-token prompt takes 53 seconds before the
first word of the answer.

**So it suits generation, not long prompts.** Which is the wrong
way round for an agent, since an agent sends whole files.

**Let llama.cpp choose the split.** Given a number it will not
adjust it: `n_gpu_layers already set by user to 28, abort`, followed
by a failure to allocate 26 664 MiB on a 32 623 MiB card. With the
setting left on -2 the flag is not passed at all, llama.cpp measures
the free memory itself, and the model runs.
