# Results

Every number here was produced by a script in `harness/` and is in
`results/` as JSON. Nothing was typed in by hand.

## The models

| Model | Engine | Format | Load | Unload |
|---|---|---|---:|---:|
| GLM-4.7-Flash | vLLM | NVFP4 | 98.3 s | 2.3 s |
| Gemma-4-26B-A4B | llama.cpp | GGUF | 9.3 s | 2.5 s |
| Gemma-4-26B-A4B | vLLM | NVFP4 | 45.1 s | 2.1 s |
| Gemma-4-E4B | llama.cpp | GGUF | 3.3 s | 2.4 s |
| Qwen3-Coder-30B-A3B | vLLM | NVFP4 | 45.1 s | 2.0 s |
| Qwen3.6-35B-A3B | llama.cpp | GGUF | 10.8 s | 2.6 s |
| Qwen3.6-35B-A3B | vLLM | NVFP4 | 98.1 s | 2.3 s |
| Qwopus3.6-27B-Coder | vLLM | NVFP4 | 69.6 s | 2.2 s |
| Coder-Next 80B | llama.cpp | GGUF | 0.1 s | — s |

The last entry was loaded and unloaded but not tested. It is here to
show that a model far larger than the card runs at all, and what that
costs before it answers anything.

**Did not start:** Coder-Next 80B (llama.cpp) — Qwen3-Coder-Next-UD-Q4_K_XL needs about 46.2 GB but only 31.9 GB is free on the card. Unload another model, or choose a smaller one.

## Quality, and what each run cost

One pass per model per test. Correctness and speed come out of the same
pass, because both are the answer to how this machine behaves.

### Classification — SIB-200, twenty languages

Is this sentence about politics? About one in seven is, so a model that
always says no scores 86% accuracy and nothing else. F1 is the column
that matters.

| Model | Engine | F1 | Accuracy | Sentences/s | Prompt tok/s | Wall |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.819** | 0.941 | 36.97 | 3514.9 | 110.35 s |
| Gemma-4-26B-A4B | llama.cpp | **0.871** | 0.963 | 8.94 | 662.2 | 456.41 s |
| Gemma-4-26B-A4B | vLLM | **0.875** | 0.964 | 51.13 | 3797.8 | 79.79 s |
| Gemma-4-E4B | llama.cpp | **0.828** | 0.945 | 11.62 | 851.2 | 351.22 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.726** | 0.933 | 49.9 | 4756.3 | 81.76 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.895** | 0.969 | 8.03 | 626.1 | 507.86 s |
| Qwen3.6-35B-A3B | vLLM | **0.889** | 0.967 | 53.6 | 4507.8 | 76.11 s |
| Qwopus3.6-27B-Coder | vLLM | **0.906** | 0.971 | 19.69 | 1531.0 | 207.2 s |

### Comprehension — Belebele, twenty languages

A passage, a question, four answers. Guessing scores 0.25.

| Model | Engine | Accuracy | Questions/s | Wall |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.742** | 32.97 | 60.66 s |
| Gemma-4-26B-A4B | llama.cpp | **0.884** | 9.45 | 207.13 s |
| Gemma-4-26B-A4B | vLLM | **0.873** | 59.08 | 33.13 s |
| Gemma-4-E4B | llama.cpp | **0.760** | 18.12 | 110.35 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.847** | 59.54 | 33.59 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.913** | 4.33 | 461.76 s |
| Qwen3.6-35B-A3B | vLLM | **0.895** | 30.53 | 65.51 s |
| Qwopus3.6-27B-Coder | vLLM | **0.915** | 19.92 | 100.41 s |

### Translation — FLORES-200, English into nineteen languages

chrF++ against translations made by people.

| Model | Engine | chrF++ | Translations/s | Wall |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **50.39** | 7.11 | 133.63 s |
| Gemma-4-26B-A4B | llama.cpp | **56.12** | 2.71 | 350.82 s |
| Gemma-4-26B-A4B | vLLM | **55.80** | 11.59 | 81.96 s |
| Gemma-4-E4B | llama.cpp | **54.08** | 3.35 | 283.69 s |
| Qwen3-Coder-30B-A3B | vLLM | **45.38** | 8.25 | 115.15 s |
| Qwen3.6-35B-A3B | llama.cpp | **54.24** | 1.93 | 492.87 s |
| Qwen3.6-35B-A3B | vLLM | **53.79** | 9.65 | 98.49 s |
| Qwopus3.6-27B-Coder | vLLM | **52.99** | 5.03 | 188.89 s |

### Coding — HumanEval+ and MBPP+

541 problems, marked by running the code against the set's own tests.

| Model | Engine | Pass rate | Passed | HumanEval+ | MBPP+ | Wall |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.706** | 382/541 | 0.749 | 0.688 | 203.94 s |
| Gemma-4-26B-A4B | llama.cpp | **0.834** | 451/541 | 0.951 | 0.783 | 688.64 s |
| Gemma-4-26B-A4B | vLLM | **0.826** | 447/541 | 0.945 | 0.775 | 219.86 s |
| Gemma-4-E4B | llama.cpp | **0.765** | 414/541 | 0.877 | 0.717 | 674.73 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.791** | 428/541 | 0.890 | 0.749 | 153.6 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.808** | 437/541 | 0.902 | 0.767 | 486.95 s |
| Qwen3.6-35B-A3B | vLLM | **0.810** | 438/541 | 0.902 | 0.770 | 147.69 s |
| Qwopus3.6-27B-Coder | vLLM | **0.815** | 441/541 | 0.932 | 0.765 | 304.9 s |

## Where the languages differ

The average hides the useful part. These are the per-language F1 scores
from the classification run, which is where a model that only pretends to
read a language shows itself.

| Model | ar | bn | de | en | es | fr | hi | ja | ko | lt | pl | pt | ro | ru | ta | th | tr | uk | vi | zh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GLM-4.7-Flash (vLLM) | 0.79 | 0.84 | 0.79 | 0.84 | 0.80 | 0.88 | 0.86 | 0.79 | 0.85 | 0.84 | 0.79 | 0.84 | 0.80 | 0.79 | 0.90 | 0.79 | 0.71 | 0.85 | 0.83 | 0.81 |
| Gemma-4-26B-A4B (llama.cpp) | 0.88 | 0.80 | 0.86 | 0.85 | 0.92 | 0.86 | 0.84 | 0.86 | 0.87 | 0.84 | 0.94 | 0.90 | 0.86 | 0.88 | 0.85 | 0.88 | 0.85 | 0.86 | 0.89 | 0.92 |
| Gemma-4-26B-A4B (vLLM) | 0.92 | 0.88 | 0.85 | 0.89 | 0.92 | 0.83 | 0.86 | 0.86 | 0.85 | 0.88 | 0.90 | 0.88 | 0.83 | 0.88 | 0.87 | 0.88 | 0.86 | 0.84 | 0.89 | 0.92 |
| Gemma-4-E4B (llama.cpp) | 0.88 | 0.75 | 0.83 | 0.83 | 0.86 | 0.85 | 0.80 | 0.80 | 0.83 | 0.84 | 0.83 | 0.79 | 0.77 | 0.80 | 0.86 | 0.85 | 0.80 | 0.82 | 0.88 | 0.88 |
| Qwen3-Coder-30B-A3B (vLLM) | 0.73 | 0.64 | 0.72 | 0.76 | 0.77 | 0.77 | 0.65 | 0.64 | 0.69 | 0.72 | 0.68 | 0.73 | 0.72 | 0.67 | 0.73 | 0.73 | 0.72 | 0.80 | 0.80 | 0.81 |
| Qwen3.6-35B-A3B (llama.cpp) | 0.92 | 0.90 | 0.88 | 0.92 | 0.94 | 0.87 | 0.87 | 0.87 | 0.92 | 0.86 | 0.89 | 0.87 | 0.88 | 0.88 | 0.92 | 0.89 | 0.90 | 0.90 | 0.92 | 0.92 |
| Qwen3.6-35B-A3B (vLLM) | 0.90 | 0.83 | 0.88 | 0.90 | 0.94 | 0.92 | 0.88 | 0.89 | 0.92 | 0.84 | 0.89 | 0.90 | 0.88 | 0.88 | 0.79 | 0.87 | 0.90 | 0.92 | 0.92 | 0.92 |
| Qwopus3.6-27B-Coder (vLLM) | 0.92 | 0.92 | 0.91 | 0.92 | 0.91 | 0.92 | 0.91 | 0.90 | 0.92 | 0.91 | 0.88 | 0.94 | 0.95 | 0.89 | 0.83 | 0.88 | 0.94 | 0.89 | 0.94 | 0.88 |

## Throughput against concurrency

The same classification work at rising concurrency, on three languages in
three writing systems. This is the measurement that says what the engine
does, rather than what the model knows.

| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 10.6 | 56.6 | 149.2 | 165.7 | **15.7x** |
| Gemma-4-26B-A4B | llama.cpp | 9.4 | 9.5 | 9.6 | 9.8 | **1.0x** |
| Gemma-4-26B-A4B | vLLM | 8.7 | 54.4 | 164.7 | 169.7 | **19.6x** |
| Gemma-4-E4B | llama.cpp | 11.7 | 12.4 | 12.4 | 12.4 | **1.1x** |
| Qwen3-Coder-30B-A3B | vLLM | 12.0 | 62.0 | 175.6 | 176.6 | **14.7x** |
| Qwen3.6-35B-A3B | llama.cpp | 8.0 | 8.1 | 8.4 | 8.1 | **1.0x** |
| Qwen3.6-35B-A3B | vLLM | 14.8 | 60.0 | 105.3 | 105.7 | **7.1x** |
| Qwopus3.6-27B-Coder | vLLM | 3.2 | 19.4 | 43.8 | 43.9 | **13.5x** |

## A model larger than the card

`Qwen3-Coder-Next-UD-Q4_K_XL.gguf` is **46.2 GB** on a card with 32 GB. AI-Lab refuses to
load it, on purpose: this GPU is attached over an OCuLink cable, and a
model split between card and system memory sends every token across that
link. The refusal is a design decision, so it is worth knowing what the
decision costs.

Measured outside AI-Lab, with llama.cpp started by hand:

| Split | Loaded | VRAM | Generation |
|---|---:|---:|---:|
| chosen by llama.cpp | 10.5 s | 30728 MB | 42.0 tok/s |

**Do not force the split.** Told to put a fixed number of layers on the
card, llama.cpp gives up rather than fit — *"n_gpu_layers already set by
user to 36, abort"* — and then fails trying to allocate 34 GB on a 32 GB
card. Left alone, it works out the split itself and the model runs.

The loading time above is warm: the file was already in the page cache
from earlier attempts. A first read of 46 GB from disk is slower.
