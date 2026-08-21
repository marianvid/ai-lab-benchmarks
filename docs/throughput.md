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
| GLM-4.7-Flash | vLLM | 10.0 | 44.6 | 86.6 | 87.3 | **8.7×** |
| Gemma-4-26B-A4B | llama.cpp | 9.4 | 9.5 | 9.5 | 9.4 | **1.0×** |
| Gemma-4-26B-A4B | vLLM | 8.7 | 50.5 | 120.5 | 121.3 | **13.9×** |
| Gemma-4-31B | llama.cpp | 2.4 | 2.4 | 2.4 | 2.4 | **1.0×** |
| Gemma-4-31B | vLLM | 2.9 | 18.1 | 47.5 | 47.8 | **16.4×** |
| Gemma-4-E4B | llama.cpp | 11.6 | 11.7 | 11.7 | 11.7 | **1.0×** |
| Qwen3-Coder-30B-A3B | vLLM | 12.1 | 58.7 | 129.2 | 126.1 | **10.7×** |
| Qwen3.6-35B-A3B | llama.cpp | 8.0 | 8.2 | 8.1 | 8.1 | **1.0×** |
| Qwen3.6-35B-A3B | vLLM | 14.9 | 60.9 | 106.5 | 107.4 | **7.2×** |
| Qwopus3.6-27B-Coder | vLLM | 3.3 | 19.7 | 44.3 | 44.6 | **13.6×** |

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
| GLM-4.7-Flash | vLLM | 10.2 | 15.3 | 15.4 | 15.4 | **1.5×** |
| Gemma-4-26B-A4B | llama.cpp | 2.9 | 2.9 | 2.9 | 2.9 | **1.0×** |
| Gemma-4-26B-A4B | vLLM | 9.7 | 13.0 | 13.2 | 13.2 | **1.4×** |
| Gemma-4-31B | llama.cpp | 0.6 | 0.6 | 0.6 | 0.6 | **1.0×** |
| Gemma-4-31B | vLLM | 3.4 | 4.4 | 4.4 | 4.4 | **1.3×** |
| Gemma-4-E4B | llama.cpp | 5.8 | 6.0 | 6.0 | 6.0 | **1.0×** |
| Qwen3-Coder-30B-A3B | vLLM | 10.9 | 14.3 | 14.3 | 14.3 | **1.3×** |
| Qwen3.6-35B-A3B | llama.cpp | 1.8 | 1.8 | 1.8 | 1.8 | **1.0×** |
| Qwen3.6-35B-A3B | vLLM | 8.7 | 12.9 | 13.0 | 12.9 | **1.5×** |
| Qwopus3.6-27B-Coder | vLLM | 3.9 | 5.7 | 5.7 | 5.7 | **1.5×** |

**Long prompts take the batching advantage away, from every
engine.** On sentences vLLM gains 7× to 16×. On articles the same
models gain 1.3× to 1.5×, and it is spent by the eighth request:
c=8, c=32 and c=64 are the same number.

An article fills far more [KV cache](glossary.md#kv-cache) than a
sentence, so far fewer requests fit on the card at once. Past that
point the extra ones queue, and queueing is not throughput.

**This is the table to plan document work from.** The sentence
ladder describes a workload of short prompts, and using its gains
to size a job that sends whole files will overstate what the card
does by an order of magnitude.

## Prompt reading as concurrency rises

The same long-prompt runs, reporting prompt reading rather than
articles finished. [Prefill](glossary.md#prefill "prompt reading, tokens per second") (tok/s).

| Model | Engine | c=1 | c=8 | c=32 | c=64 |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 12830.8 | 19220.1 | 19307.3 | 19341.3 |
| Gemma-4-26B-A4B | llama.cpp | 3624.8 | 3683.5 | 3675.9 | 3686.9 |
| Gemma-4-26B-A4B | vLLM | 12162.8 | 16381.2 | 16624.1 | 16569.8 |
| Gemma-4-31B | llama.cpp | 731.7 | 731.4 | 732.1 | 735.8 |
| Gemma-4-31B | vLLM | 4247.2 | 5555.2 | 5557.7 | 5564.6 |
| Gemma-4-E4B | llama.cpp | 7300.9 | 7528.5 | 7536.4 | 7551.3 |
| Qwen3-Coder-30B-A3B | vLLM | 16778.5 | 22041.7 | 21913.9 | 21926.5 |
| Qwen3.6-35B-A3B | llama.cpp | 2327.0 | 2347.1 | 2347.1 | 2338.7 |
| Qwen3.6-35B-A3B | vLLM | 11223.6 | 16697.8 | 16773.9 | 16635.1 |
| Qwopus3.6-27B-Coder | vLLM | 5028.7 | 7360.1 | 7393.6 | 7406.0 |

**A prefill rate needs the concurrency it was measured at.** On
vLLM, reading eight articles together is 1.2× to 1.4× faster per
token than reading one; past eight it stops improving. On
llama.cpp the figure does not move at all.

These are aggregate rates — every prompt token in the run divided
by the wall clock — so they say how much text the card gets
through, not how quickly any one request is answered. For that,
see [latency.md](latency.md).

