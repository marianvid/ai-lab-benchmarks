# Findings

## Engine dominates throughput; model dominates quality

The same model file run on both engines. `Cls F1` is the classification score
(0–1); `items/s` is sentences classified per second at concurrency 8. Anything
else about the model is held constant — same weights, same prompts, same
machine.

| Model | Engine | Cls F1 | items/s |
|---|---|---:|---:|
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 8.9 |
| Gemma-4-26B-A4B | vLLM | 0.875 | 51.1 |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

F1 delta is within noise (±0.006). Throughput delta is 5.7× and 6.7×.

## Continuous batching accounts for it

Throughput measured at 1, 8, 32 and 64 requests in flight, then expressed as
the ratio of the highest to the lowest — how much each engine gained from being
given more work at once:

- vLLM: 7.1× – 19.6×
- llama.cpp: 1.0× – 1.1×

llama.cpp allocates a fixed number of slots and divides the context window
between them, so extra requests queue. vLLM keeps a shared paged pool and adds
or retires requests inside a running batch. At concurrency 1 the two are
comparable; the gap is entirely about parallel requests.

## llama.cpp wins on startup

Seconds from the load request to the engine answering, across the models
measured. vLLM spends the extra time compiling kernels for the specific model
and card.

| Engine | Load |
|---|---|
| llama.cpp | 3.3 – 10.8 s |
| vLLM | 45.1 – 98.3 s |

Unload is 2.0 – 2.6 s for both. For load-ask-unload cycles llama.cpp finishes
before vLLM has started; break-even against vLLM's throughput advantage is
roughly 90 s of sustained batched work.

## A code-specialised model is a poor language model

Qwen3-Coder-30B-A3B has the highest prompt-reading rate in the set. Its scores
against the best result in each task, all measured in the same run:

| | best | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | 0.726 |
| chrF++ | 56.12 | 45.38 |
| Comprehension | 0.915 | 0.847 |
| Coding pass rate | 0.834 | 0.791 |

It is not even the best coder in the set.

## Parameter count buys comprehension, not much else

Gemma-4-E4B is 4.6 GB on disk; the leading model is 20 GB. Same tasks, same
scales as above:

| | E4B (4.6 GB) | best |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding | 0.765 | 0.834 |
| Comprehension | 0.760 | 0.915 |

Classification and coding are within 8 points. Comprehension is 15.5 points
down — the MCQ task is the one that separates by capacity.

## Tokenizer cost is not predicted by script

Token counts for identical sentences, as a multiple of the English count. 1.50
means the same content costs half again as many tokens, so a context window
holds two thirds as much:

Han 1.12, Devanagari 1.31, Cyrillic 1.40–1.64, Latin 1.00–1.66.

Lithuanian (Latin) is the most expensive of the 20; Chinese (Han) the cheapest
after English. The predictor is tokenizer coverage, not writing system.

Consequence: context windows sized on English under-provision for Baltic, Thai
and Ukrainian by up to 40%.

## Oversize models run if the engine picks the split

llama.cpp can keep part of a model on the card and the rest in system memory.
A 46.2 GB model on a 32 GB card: 56.4 output tokens per second, 30 728 MB of
the card in use.

Forcing `--n-gpu-layers` to a fixed number makes it abort rather than fit —
it will not adjust a figure the user supplied.

## Selection

Which combination to pick, given the numbers above.

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
