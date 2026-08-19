# Findings

## Engine dominates throughput; model dominates quality

Same weights, both engines:

| Model | Engine | Cls F1 | items/s |
|---|---|---:|---:|
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 8.9 |
| Gemma-4-26B-A4B | vLLM | 0.875 | 51.1 |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

F1 delta is within noise (±0.006). Throughput delta is 5.7× and 6.7×.

## Continuous batching accounts for it

Concurrency 1 → 64, classification:

- vLLM: 7.1× – 19.6×
- llama.cpp: 1.0× – 1.1×

llama.cpp allocates a fixed slot count and splits the context window between
them; vLLM uses a shared paged pool with continuous batching. At concurrency 1
the engines are comparable.

## llama.cpp wins on startup

| Engine | Load |
|---|---|
| llama.cpp | 3.3 – 10.8 s |
| vLLM | 45.1 – 98.3 s |

Unload is 2.0 – 2.6 s for both. For load-ask-unload cycles, llama.cpp finishes
before vLLM has started. Break-even against vLLM's throughput advantage is
roughly 90 s of sustained batched work.

## A code-specialised model is a poor language model

Qwen3-Coder-30B-A3B, highest prompt-read rate in the set:

| | best | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | 0.726 |
| chrF++ | 56.12 | 45.38 |
| Comprehension | 0.915 | 0.847 |
| Coding pass rate | 0.834 | 0.791 |

It is not even the best coder in the set.

## Parameter count buys comprehension, not much else

Gemma-4-E4B is 4.6 GB against 20 GB for the leader:

| | E4B (4.6 GB) | best |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding | 0.765 | 0.834 |
| Comprehension | 0.760 | 0.915 |

Classification and coding are within 8 points. Comprehension is 15.5 points
down — the MCQ task is the one that separates by capacity.

## Tokenizer cost is not predicted by script

Tokens for identical content, relative to English: Han 1.12, Devanagari 1.31,
Cyrillic 1.40–1.64, Latin 1.00–1.66.

Lithuanian (Latin) is the most expensive of the 20; Chinese (Han) the cheapest
after English. The predictor is tokenizer coverage, not writing system.

Consequence: context windows sized on English under-provision for Baltic, Thai
and Ukrainian by up to 40%.

## Oversize models run if the engine picks the split

46.2 GB model, 32 GB card, 56.4 tok/s generation, 30 728 MB resident.
Forcing `--n-gpu-layers` makes llama.cpp abort instead of fitting.

## Selection

| Workload | Choice |
|---|---|
| Batched multilingual bulk | Gemma-4-26B-A4B on vLLM — 0.875 F1 at 51 items/s |
| Highest quality, throughput secondary | Qwopus3.6-27B-Coder on vLLM — 0.906 / 0.915, 19.7 items/s |
| Single request, low latency | any model on llama.cpp |
| Agent prompt-reading | Qwen3-Coder-30B-A3B; not for prose |
| Already on Qwen3.6-35B | switch engine before switching model: 6.7× for −0.006 F1 |

## Not covered

Long-context behaviour, multi-turn, agent loops, languages outside the 20,
error bars.
