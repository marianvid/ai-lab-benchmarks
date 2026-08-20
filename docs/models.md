# Models

Ten combinations of model and engine. Three models appear in both formats, so
the engine can be compared with everything else held constant.

| Model | Engine | Format | On disk | Parameters | Kind |
|---|---|---|---:|---|---|
| Gemma-4-26B-A4B | vLLM | NVFP4 | 18 GB | 26B total, 4B active | MoE |
| Gemma-4-26B-A4B | llama.cpp | GGUF Q4_K_XL | 16 GB | 26B total, 4B active | MoE |
| Qwopus3.6-27B-Coder | vLLM | NVFP4 | 20 GB | 27B | dense |
| Qwen3-Coder-30B-A3B | vLLM | NVFP4 | 17 GB | 30B total, 3B active | MoE |
| Qwen3.6-35B-A3B | vLLM | NVFP4 | 22 GB | 35B total, 3B active | MoE |
| Qwen3.6-35B-A3B | llama.cpp | GGUF Q4_K_M | 21 GB | 35B total, 3B active | MoE |
| Gemma-4-E4B | llama.cpp | GGUF Q4_0 | 4.3 GB | ~4B | dense |
| GLM-4.7-Flash | vLLM | NVFP4 | 20 GB | ~30B total, ~3.6B active¹ | MoE |
| Gemma-4-31B | vLLM | NVFP4 | 22 GB | 31B, all active | dense |
| Gemma-4-31B | llama.cpp | GGUF Q4_K_XL | 18 GB | 31B, all active | dense |

¹ GLM-4.7-Flash publishes no parameter count. This one is computed from its
`config.json`: 47 layers, 64 experts of which 4 are active per token plus one
shared. Treat it as an estimate.

Sizes are the files on disk. A running model needs more than that: the weights
plus a [KV cache](glossary.md#kv-cache) sized by the context window and the
number of requests in flight.

vLLM was configured to claim 90% of the card at startup regardless of the
model, so its VRAM figures describe the setting, not the model.

## Selection

| Model | Why it is here |
|---|---|
| Gemma-4-26B-A4B | measured on both engines, so the engine's effect can be isolated |
| Qwen3.6-35B-A3B | the same, and the model in production use here — the baseline |
| Qwopus3.6-27B-Coder | dense and reasoning-tuned, unlike the rest |
| Qwen3-Coder-30B-A3B | code-specialised, to test whether it is usable for language work |
| Gemma-4-E4B | a quarter the size of the others |
| GLM-4.7-Flash | weakest on most tasks; a set with no weak entry shows nothing about its own resolution |
| Gemma-4-31B | the only large dense model here, on both engines. Everything else of this size computes 3-4B parameters per token; this one computes all 31B |

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

Gemma-4-31B was added after the others and ran everything at 32 768. Its NVFP4
instance also ran with `language_model_only`, which skips the image half of the
model: vLLM otherwise pushes invented pictures through it at startup to measure
that path, and none of these tests send a picture.

`Qwen3-Coder-Next`, 46 GB, was loaded and timed but not tested — it exceeds VRAM
and runs only with part of it in system memory. See
[loading.md](loading.md#a-model-larger-than-vram).
