# Throughput

How much work each combination completes per second, and how that
changes when more requests arrive at once.

Two ladders, because prompt length changes the answer. Short prompts are
single sentences; long prompts are whole Wikipedia articles of 2 000 to
5 000 characters. The prompt fills the
[KV cache](glossary.md#kv-cache), and the cache limits how many requests
an engine holds at once.

## Short prompts — sentences

Classification on English, Russian and Chinese, repeated at 1, 8, 32 and
64 requests in flight. Figures are sentences per second.

| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 10.6 | 56.6 | 149.2 | 165.7 | **15.7×** |
| Gemma-4-26B-A4B | llama.cpp | 9.4 | 9.5 | 9.6 | 9.8 | **1.0×** |
| Gemma-4-26B-A4B | vLLM | 8.7 | 54.4 | 164.7 | 169.7 | **19.6×** |
| Gemma-4-E4B | llama.cpp | 11.7 | 12.4 | 12.4 | 12.4 | **1.1×** |
| Qwen3-Coder-30B-A3B | vLLM | 12.0 | 62.0 | 175.6 | 176.6 | **14.7×** |
| Qwen3.6-35B-A3B | llama.cpp | 8.0 | 8.1 | 8.4 | 8.1 | **1.0×** |
| Qwen3.6-35B-A3B | vLLM | 14.8 | 60.0 | 105.3 | 105.7 | **7.1×** |
| Qwopus3.6-27B-Coder | vLLM | 3.2 | 19.4 | 43.8 | 43.9 | **13.5×** |

**Gain is the highest rate divided by the lowest**: what the engine got
out of being handed more work at once. A gain of 1.0 means nothing — the
ninth request waited for one of the first eight to finish.

**At one request at a time the engines are comparable.** The difference
appears only under load, from
[continuous batching](glossary.md#continuous-batching).

**vLLM stops improving between 32 and 64**: the card is saturated, and
further requests only wait longer.

## Long prompts — whole articles

The same ladder, sending complete Wikipedia articles and asking for a
one-word answer. Long input, short output: the shape of
classification, routing and tagging work on real documents. 60
articles per run, 2 165–5 227 characters, six languages.

| Model | Engine | c=1 | c=8 | c=32 | c=64 | Gain |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 10.5 | 31.4 | 49.4 | 87.8 | **8.3×** |
| Gemma-4-26B-A4B | llama.cpp | 3.0 | 3.1 | 3.8 | 3.1 | **1.3×** |
| Gemma-4-26B-A4B | vLLM | 9.9 | 108.3 | 201.9 | 229.1 | **23.2×** |
| Gemma-4-E4B | llama.cpp | 6.0 | 27.6 | 27.8 | 27.9 | **4.6×** |
| Qwen3-Coder-30B-A3B | vLLM | 11.1 | 86.3 | 174.9 | 178.5 | **16.1×** |
| Qwen3.6-35B-A3B | llama.cpp | 1.9 | 2.0 | 1.8 | 1.8 | **1.1×** |
| Qwen3.6-35B-A3B | vLLM | 8.9 | 26.8 | 30.5 | 30.7 | **3.5×** |
| Qwopus3.6-27B-Coder | vLLM | 3.9 | 6.1 | 6.5 | 5.6 | **1.6×** |

**Compare the gain columns between the two tables, not the rates.**
An article is ten to twenty times longer than a sentence, so fewer
finish per second either way. What changes is whether the engine
still profits from concurrency when each request holds far more
cache — for some combinations it profits more, for others barely at
all.

