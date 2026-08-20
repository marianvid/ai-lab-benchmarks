# Models

Eight combinations of model and engine. Two models appear in both formats, so
the engine can be compared with everything else held constant.

| Model | Engine | Format | On disk | Parameters | Kind |
|---|---|---|---:|---|---|
| Gemma-4-26B-A4B | vLLM | NVFP4 | 18 GB | 26B total, 4B active | MoE |
| Gemma-4-26B-A4B | llama.cpp | GGUF Q4_K_XL | 16 GB | 26B total, 4B active | MoE |
| Qwopus3.6-27B-Coder | vLLM | NVFP4 | 20 GB | 27B | dense, reasoning |
| Qwen3-Coder-30B-A3B | vLLM | NVFP4 | 17 GB | 30B total, 3B active | MoE |
| Qwen3.6-35B-A3B | vLLM | NVFP4 | 22 GB | 35B total, 3B active | MoE |
| Qwen3.6-35B-A3B | llama.cpp | GGUF Q4_K_M | 21 GB | 35B total, 3B active | Moe |
| Gemma-4-E4B | llama.cpp | GGUF Q4_0 | 4.3 GB | ~4B | dense |
| GLM-4.7-Flash | vLLM | NVFP4 | 20 GB | — | — |

Sizes are the files on disk. A running model also needs room for its
[KV cache](glossary.md#kv-cache), which is why 22 GB of weights fits on a 32 GB
card and 46 GB does not.

## Selection

| Model | Why it is here |
|---|---|
| Gemma-4-26B-A4B | measured on both engines, so the engine's effect can be isolated |
| Qwen3.6-35B-A3B | the same, and the model in production use here — the baseline |
| Qwopus3.6-27B-Coder | dense and reasoning-tuned, unlike the rest |
| Qwen3-Coder-30B-A3B | code-specialised, to test whether it is usable for language work |
| Gemma-4-E4B | a quarter the size of the others |
| GLM-4.7-Flash | weakest on most tasks; a set with no weak entry shows nothing about its own resolution |

## Terms

**Mixture of experts** — the model holds many specialised sub-networks and uses
only a few per token. "26B total, 4B active" means the file holds 26 billion
parameters and any one token is computed with about 4 billion. It occupies
memory like a 26B model and runs closer to the speed of a 4B one.

**Dense** — every parameter is used for every token. Slower per token at the
same size.

**Q4_K_XL, Q4_K_M, Q4_0** — llama.cpp quantisation recipes, all near 4 bits per
weight. XL keeps more precision in the layers that lose most from rounding;
`_0` is the simplest and smallest.

## Settings

[Context window](glossary.md#context-window) 32 768 tokens for the latency and
long-form measurements. The four quality tasks ran at 8 192, before that change;
their prompts are two or three hundred tokens, inside either setting.

vLLM instances: `gpu_memory_fraction 0.90`, `max_sequences 32`.

`Qwen3-Coder-Next`, 46 GB, was loaded and timed but not tested — it exceeds VRAM
and runs only with part of it in system memory. See
[loading.md](loading.md#a-model-larger-than-vram).
