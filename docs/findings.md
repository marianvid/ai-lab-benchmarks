# Findings

What the numbers on the other pages add up to. Every figure here is a link away
from the table it came from.

## 1. The engine decides throughput; the model decides quality

The same weights on both engines, from [quality.md](quality.md) and
[throughput.md](throughput.md):

| Model | Engine | Classification F1 | Sentences/s |
|---|---|---:|---:|
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 8.9 |
| Gemma-4-26B-A4B | vLLM | 0.875 | 51.1 |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

The F1 differences, 0.004 and 0.006, are smaller than the noise in a set of
this size. The throughput differences are 5.7× and 6.7×.

Nothing about the model changed. Same file, same prompts, same card.

## 2. The advantage comes from batching, and only from batching

At one request at a time the two engines are level. The gap opens as requests
arrive together, and it is a property of how each engine schedules them.

| Engine | Gain, 1 → 64 concurrent (sentences) |
|---|---|
| vLLM | 7.1× – 19.6× |
| llama.cpp | 1.0× – 1.1× |

llama.cpp allocates a fixed number of slots at startup and divides the context
window between them. A ninth request waits. vLLM keeps a shared pool and adds
requests to a batch already in flight; a request that finishes frees its space
immediately.

## 3. Prompt length changes that answer, sometimes completely

The same ladder run twice: once with single sentences, once with whole articles
of 2 000 to 5 000 characters.

| Model | Engine | Gain on sentences | Gain on articles |
|---|---|---:|---:|
| Gemma-4-26B-A4B | vLLM | 19.6× | **23.2×** |
| Qwen3-Coder-30B-A3B | vLLM | 14.7× | **16.1×** |
| GLM-4.7-Flash | vLLM | 15.7× | **8.3×** |
| Qwen3.6-35B-A3B | vLLM | 7.1× | **3.5×** |
| Qwopus3.6-27B-Coder | vLLM | 13.5× | **1.6×** |
| Gemma-4-E4B | llama.cpp | 1.1× | 4.6× |
| Gemma-4-26B-A4B | llama.cpp | 1.0× | 1.3× |
| Qwen3.6-35B-A3B | llama.cpp | 1.0× | 1.1× |

**Qwopus goes from 13.5× to 1.6×.** A long prompt occupies far more
[KV cache](glossary.md#kv-cache) than a sentence, so fewer requests fit on the
card at once. A model whose cache is already large per request runs out of room
first, and the batching advantage disappears with it.

**Benchmarking an engine on short prompts and then deploying it on documents
will not give you the throughput you measured.** For some combinations it is
better, for others eight times worse. This is the measurement most easily
skipped and most easily wrong.

## 4. Cold and warm loads are different measurements

From [loading.md](loading.md), with the host's page cache dropped before the
run:

| Model | Engine | Cold | Warm |
|---|---|---:|---:|
| Gemma-4-26B-A4B | vLLM | 212.4 s | 117.4 s |
| Qwen3.6-35B-A3B | vLLM | 177.0 s | 92.2 s |
| Qwopus3.6-27B-Coder | vLLM | 163.4 s | 69.1 s |
| Qwen3.6-35B-A3B | llama.cpp | 10.8 s | 5.3 s |
| Gemma-4-26B-A4B | llama.cpp | 9.0 s | 5.0 s |
| Gemma-4-E4B | llama.cpp | 3.9 s | 2.5 s |

**A cold vLLM start costs roughly twice a warm one**, and the extra is not just
the model file. vLLM's own installation is several gigabytes of Python and CUDA
libraries, and after a cold cache those have to be read as well. llama.cpp is a
single binary and pays almost none of that.

**Quote a load time without saying which it was and it means very little.** The
gap here is 95 seconds for one model.

## 5. llama.cpp wins whenever you are not batching

3 to 11 seconds against 42 to 212. For work that loads a model, asks one
question and unloads, llama.cpp has finished before vLLM has started.

The crossover is roughly 90 seconds of sustained batched work: beyond that,
vLLM's throughput has repaid its startup.

## 6. A code-specialised model is a poor language model

Qwen3-Coder-30B-A3B reads prompts faster than anything else measured and is
last at every language task.

| | Best in set | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | **0.726** |
| Translation chrF++ | 56.12 | **45.38** |
| Comprehension | 0.915 | 0.847 |
| Coding pass rate | 0.834 | 0.791 |

It is not even the best coder in the set. Gemma-4-26B-A4B, a general model,
passes more Python problems than it does.

## 7. Size buys comprehension more than anything else

Gemma-4-E4B is 4.3 GB; the leading models are 16 to 22 GB.

| | E4B (4.3 GB) | Best |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding pass rate | 0.765 | 0.834 |
| Comprehension | **0.760** | **0.915** |

Classification and coding are within 8 points. Comprehension is 15.5 points
behind, and after subtracting the 0.25 that guessing scores, the gap is larger
still: 0.51 above chance against 0.66.

Comprehension is the task that cannot be pattern-matched, and it is where a
small model actually costs you something.

## 8. A context window is worth less in some languages

From [tokenizer.md](tokenizer.md), tokens for identical sentences relative to
English:

| | |
|---|---|
| Chinese (Han) | 1.12× |
| Japanese | 1.24× |
| Hindi (Devanagari) | 1.31× |
| Russian (Cyrillic) | 1.40× |
| Ukrainian (Cyrillic) | 1.64× |
| Thai | 1.65× |
| **Lithuanian (Latin)** | **1.66×** |

The writing system does not predict this. Chinese is the cheapest language
measured after English; the most expensive is written in the same alphabet as
English. What decides it is how much of that language the tokenizer was built
from.

**An 8 192-token window holds about 60% as much Lithuanian as English.** Size a
window on English documents and it will reject Baltic or Thai text in a way that
looks like a model fault.

## 9. A model larger than VRAM runs, if the engine picks the split

46.2 GB on a 32 GB card, 56.4 tokens per second generated, with llama.cpp
keeping part of the model in system memory.

Given a fixed `--n-gpu-layers` it refuses to fit and dies trying to allocate
34 GB. Left alone it works the division out itself.

## Choosing

| Workload | Choice | Why |
|---|---|---|
| Batched multilingual bulk | Gemma-4-26B-A4B on vLLM | 0.875 F1 at 51 sentences/s, and the only model whose batching gain *improves* on long prompts |
| Highest quality, speed secondary | Qwopus3.6-27B-Coder on vLLM | 0.906 F1 and 0.915 comprehension, but 1.6× batching gain on articles — do not plan on concurrency |
| One request at a time | any model on llama.cpp | answering while vLLM is still starting |
| Agent prompt-reading | Qwen3-Coder-30B-A3B | fastest prefill; keep it away from prose |
| Already running Qwen3.6-35B | change engine before changing model | 6.7× throughput for 0.006 F1 |

## What this does not tell you

- **One run per cell.** No error bars. Differences under 0.02 F1 are noise.
- **Single-turn only.** No agent loops, no long conversations.
- **Twenty languages.** Nothing about low-resource languages, where models
  differ far more.
- **Quality was measured at an 8 192-token context**, latency and the long-form
  ladder at 32 768. Both are stated where they apply.
