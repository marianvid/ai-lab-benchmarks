# Latency and prompt reading

**Concurrency 1** — one request, nothing else in flight — at three
prompt sizes. What a person or an agent waiting for a single answer
experiences.

**Read the prefill column with that in mind.** Prompt reading gets much
faster when several requests are read together: on Qwen3.6-35B under
vLLM it goes from 11 421 tokens per second here to 39 596 at 64
requests in flight. The figures at every step of that ladder are in
[throughput.md](throughput.md#prompt-reading-as-concurrency-rises).

The prompt is Python source repeated to length, followed by a request
to rewrite one function: the shape of an agent pasting a codebase into
every turn.

## short prompt (~500 tok)

| Model | Engine | Prompt tokens | [TTFT](glossary.md#ttft "time to first token, seconds") | [Prefill](glossary.md#prefill "prompt reading, tokens per second") | [Decode](glossary.md#decode "answer generation, tokens per second") |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 306 | 0.51 s | 595.3 | 135.9 |
| Gemma-4-26B-A4B | llama.cpp | 358 | 0.05 s | 7507.9 | 135.7 |
| Gemma-4-26B-A4B | vLLM | 358 | 0.02 s | 16943.8 | 105.2 |
| Gemma-4-31B | llama.cpp | 358 | 0.25 s | 1417.3 | 35.8 |
| Gemma-4-31B | vLLM | 358 | 0.04 s | 9212.7 | 34.1 |
| Gemma-4-E4B | llama.cpp | 354 | 0.02 s | 16504.4 | 149.9 |
| Qwen3-Coder-30B-A3B | vLLM | 309 | 0.02 s | 17325.7 | 151.7 |
| Qwen3.6-35B-A3B | llama.cpp | 338 | 0.06 s | 5717.3 | 171.5 |
| Qwen3.6-35B-A3B | vLLM | 338 | 0.07 s | 5094.6 | 209.5 |
| Qwopus3.6-27B-Coder | vLLM | 338 | 0.07 s | 4995.8 | 39.6 |

## medium prompt (~9k tok)

| Model | Engine | Prompt tokens | [TTFT](glossary.md#ttft "time to first token, seconds") | [Prefill](glossary.md#prefill "prompt reading, tokens per second") | [Decode](glossary.md#decode "answer generation, tokens per second") |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 7788 | 0.62 s | 12492.0 | 117.9 |
| Gemma-4-26B-A4B | llama.cpp | 9166 | 1.59 s | 5753.6 | 124.9 |
| Gemma-4-26B-A4B | vLLM | 9166 | 0.66 s | 13854.8 | 98.3 |
| Gemma-4-31B | llama.cpp | 9166 | 6.46 s | 1419.1 | 33.0 |
| Gemma-4-31B | vLLM | 9166 | 2.50 s | 3673.5 | 32.0 |
| Gemma-4-E4B | llama.cpp | 9162 | 0.98 s | 9348.6 | 134.5 |
| Qwen3-Coder-30B-A3B | vLLM | 7841 | 0.51 s | 15322.0 | 134.0 |
| Qwen3.6-35B-A3B | llama.cpp | 8566 | 2.14 s | 4009.0 | 162.6 |
| Qwen3.6-35B-A3B | vLLM | 8566 | 0.63 s | 13531.1 | 198.8 |
| Qwopus3.6-27B-Coder | vLLM | 8566 | 1.29 s | 6642.4 | 38.6 |

## long prompt (~29k tok)

| Model | Engine | Prompt tokens | [TTFT](glossary.md#ttft "time to first token, seconds") | [Prefill](glossary.md#prefill "prompt reading, tokens per second") | [Decode](glossary.md#decode "answer generation, tokens per second") |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | 24558 | 3.35 s | 7325.3 | 90.9 |
| Gemma-4-26B-A4B | llama.cpp | 29016 | 4.12 s | 7039.7 | 108.5 |
| Gemma-4-26B-A4B | vLLM | 29016 | 2.76 s | 10509.7 | 91.4 |
| Gemma-4-31B | llama.cpp | 29016 | 16.88 s | 1719.0 | 27.9 |
| Gemma-4-31B | vLLM | 29016 | 12.70 s | 2285.0 | 29.3 |
| Gemma-4-E4B | llama.cpp | 29012 | 2.76 s | 10505.8 | 110.7 |
| Qwen3-Coder-30B-A3B | vLLM | 24831 | 2.47 s | 10057.5 | 103.7 |
| Qwen3.6-35B-A3B | llama.cpp | 27116 | 5.00 s | 5422.8 | 142.3 |
| Qwen3.6-35B-A3B | vLLM | 27116 | 1.64 s | 16532.9 | 181.7 |
| Qwopus3.6-27B-Coder | vLLM | 27116 | 3.71 s | 7299.7 | 36.5 |

**The same text is a different number of tokens for each model.** The
prompt is identical; the tokenizers are not. That column is the first
place the difference in [tokenizer.md](tokenizer.md) becomes visible.

**TTFT is the number a person feels.** On a long prompt it is almost
all prompt reading — the model cannot start answering until it has read
the question.

**Prefill and decode do not move together.** Prefill processes every
token of the prompt at once and reaches thousands per second; decode
produces one token at a time and reaches tens. A machine can be strong
at one and ordinary at the other, and which matters depends entirely on
the work.

**Prefill rates fall as prompts grow.** Attention cost rises faster than
linearly with length, so reading 32 000 tokens is more than four times
the work of reading 8 000.

An error in the last table usually means the instance's
[context window](glossary.md#context-window) was smaller than the
prompt. All instances here were set to 32 768 tokens.
