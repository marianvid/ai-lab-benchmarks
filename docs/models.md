# The models

Eight combinations of model and engine. Two of them are the same model in both
formats, which is what makes an engine comparison possible: everything except
the engine is held constant.

| Model | Engine | Format | On disk | Parameters | Kind |
|---|---|---|---:|---|---|
| Gemma-4-26B-A4B | vLLM | NVFP4 | 18 GB | 26B total, 4B active | mixture of experts |
| Gemma-4-26B-A4B | llama.cpp | GGUF Q4_K_XL | 16 GB | 26B total, 4B active | mixture of experts |
| Qwopus3.6-27B-Coder | vLLM | NVFP4 | 20 GB | 27B | dense, reasoning |
| Qwen3-Coder-30B-A3B | vLLM | NVFP4 | 17 GB | 30B total, 3B active | mixture of experts, code |
| Qwen3.6-35B-A3B | vLLM | NVFP4 | 22 GB | 35B total, 3B active | mixture of experts |
| Qwen3.6-35B-A3B | llama.cpp | GGUF Q4_K_M | 21 GB | 35B total, 3B active | mixture of experts |
| Gemma-4-E4B | llama.cpp | GGUF Q4_0 | 4.3 GB | ~4B | small |
| GLM-4.7-Flash | vLLM | NVFP4 | 20 GB | — | — |

Sizes are what the files occupy on disk. A model also needs room for its
[KV cache](glossary.md#kv-cache) while running, which is why 22 GB of weights
fits on a 32 GB card but 46 GB does not.

## Why these eight

**Gemma-4-26B-A4B, both formats** — the only model measured on both engines
with a matching companion, so the engine's contribution can be separated from
the model's.

**Qwen3.6-35B-A3B, both formats** — the same again, and the model in production
use on this machine, so it is the baseline everything else is compared against.

**Qwopus3.6-27B-Coder** — dense rather than mixture-of-experts, and a reasoning
model. Included because it scored highest on language tasks.

**Qwen3-Coder-30B-A3B** — specialised for code. Included to test whether a code
model is usable for language work. It is not; see
[findings](findings.md#a-code-specialised-model-is-a-poor-language-model).

**Gemma-4-E4B** — 4.3 GB, roughly a quarter the size of the others. Included to
show what is lost by going small.

**GLM-4.7-Flash** — the weakest model in the set on most tasks. A benchmark with
no weak entry cannot demonstrate that it separates anything.

## Terms

**Mixture of experts** — the model contains many specialised sub-networks and
uses only a few for each token. "26B total, 4B active" means the file holds 26
billion parameters but any single token is computed with about 4 billion of
them. It loads and occupies memory like a 26B model and runs closer to the speed
of a 4B one.

**Dense** — every parameter is used for every token. Slower per token at the
same size, and often stronger at reasoning.

**Q4_K_XL, Q4_K_M, Q4_0** — llama.cpp's quantisation recipes, all roughly 4 bits
per weight. XL keeps more precision in the layers that matter most, `_0` is the
simplest and smallest.

## Configuration

All instances were configured with a **32 768-token
[context window](glossary.md#context-window)** for the measurements in this
repository. The quality tasks in
[quality.md](quality.md) were run at 8 192 before that change; prompt lengths
there are two or three hundred tokens, well inside either setting.

vLLM instances additionally used `gpu_memory_fraction 0.90` and
`max_sequences 32`.

## Not measured

A 46 GB model, `Qwen3-Coder-Next`, was loaded and timed but not tested — it does
not fit in VRAM and runs only with part of it in system memory. See
[loading.md](loading.md#a-model-larger-than-vram).
