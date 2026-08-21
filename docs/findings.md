# Findings

Every figure here is one link from the table it came from.

## 1. Throughput follows the engine, quality follows the model

The same weights on both engines, from [quality.md](quality.md) and
[throughput.md](throughput.md):

| Model | Engine | Classification F1 | Sentences/s |
|---|---|---:|---:|
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 8.9 |
| Gemma-4-26B-A4B | vLLM | 0.875 | 51.1 |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

The F1 differences, 0.004 and 0.006, are below this set's noise floor. The
throughput differences are 5.7× and 6.7×. Same file, same prompts, same card.

## 2. The advantage is batching

At one request at a time the two engines are level. The gap opens as requests
arrive together.

| Engine | Gain, 1 → 64 concurrent (sentences) |
|---|---|
| vLLM | 7.2× – 16.4× |
| llama.cpp | 1.0× |

llama.cpp allocates a fixed number of slots at startup and divides the context
window between them, so a ninth request waits. vLLM keeps a shared pool and adds
requests to a batch already in flight; one that finishes frees its space at
once.

## 3. Long prompts take that advantage away

The same ladder run twice: once with single sentences, once with whole articles
of 2 000 to 5 000 characters.

| Model | Engine | Gain on sentences | Gain on articles |
|---|---|---:|---:|
| Gemma-4-31B | vLLM | 16.4× | **1.3×** |
| Gemma-4-26B-A4B | vLLM | 13.9× | **1.4×** |
| Qwopus3.6-27B-Coder | vLLM | 13.6× | **1.5×** |
| Qwen3-Coder-30B-A3B | vLLM | 10.7× | **1.3×** |
| GLM-4.7-Flash | vLLM | 8.7× | **1.5×** |
| Qwen3.6-35B-A3B | vLLM | 7.2× | **1.5×** |
| every llama.cpp entry | llama.cpp | 1.0× | 1.0× |

Seven to sixteen times on sentences, and between 1.3 and 1.5 on articles —
every model, both engines. The gain is also spent by the eighth request: c=8,
c=32 and c=64 are the same number in every row.

An article fills far more [KV cache](glossary.md#kv-cache) than a sentence, so
far fewer requests fit on the card at once. Beyond that point the rest queue.

**Size document work from the article ladder, not the sentence one.** They
differ by an order of magnitude, and the sentence figure is the flattering one.

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

A cold vLLM start costs roughly twice a warm one. The cause of the gap was not
measured: it is somewhere between reading the weights, reading vLLM's own
multi-gigabyte installation, and rebuilding its compiled-kernel cache. The
inconsistency across models — 95 s for one, 5 s for another of the same size —
means the disk alone does not explain it.

A load time quoted without saying which it was means little. The gap here is
95 seconds for one model.

## 5. llama.cpp starts faster by an order of magnitude

3 to 11 seconds against 42 to 212. For work that loads a model, asks one question
and unloads, llama.cpp finishes before vLLM has started.

The crossover is roughly 90 seconds of sustained batched work; beyond that vLLM's
throughput has repaid its startup.

## 6. A code-specialised model is a poor language model

Qwen3-Coder-30B-A3B reads prompts faster than anything else measured and is
last at every language task.

| | Best in set | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | **0.726** |
| Translation chrF++ | 56.12 | **45.38** |
| Comprehension | 0.915 | 0.847 |
| Coding pass rate | 0.834 | 0.791 |

It is not the best coder in the set either: Gemma-4-26B-A4B, a general model,
passes more Python problems.

## 7. Size shows up in comprehension, not elsewhere

Gemma-4-E4B is 4.3 GB; the leading models are 16 to 22 GB.

| | E4B (4.3 GB) | Best |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding pass rate | 0.765 | 0.834 |
| Comprehension | **0.760** | **0.916** |

Classification and coding are within 8 points. Comprehension is 15.6 points
behind, and after subtracting the 0.25 that guessing scores the gap is larger
still: 0.51 above chance against 0.66.

Comprehension cannot be pattern-matched from a keyword, which is where the small
model's capacity runs out.

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
measured after English, and the most expensive uses the same alphabet as English.
What decides it is how much of that language the tokenizer was built from.

An 8 192-token window holds about 60% as much Lithuanian as English. A window
sized on English documents rejects Baltic or Thai text for length, which reads
as a model fault and is not one.

## 9. A model larger than VRAM runs on llama.cpp

46.2 GB on a 32 GB card, 56.4 tokens per second generated, with part of the model
in system memory. Given a fixed `--n-gpu-layers` llama.cpp refuses to fit and
fails trying to allocate 34 GB; left alone it works the division out itself.

This is a llama.cpp property. vLLM moves data rather than computation, so the
same split sends far more across the [OCuLink](glossary.md#oculink) cable and is
not usable — see [Configuration](machine.md).

**What it costs is uneven.** Across four sizes of one model, prompt reading fell
9.5× as layers moved off the card while generation fell only 2×, and 60% of the
prompt-reading loss came from the first four layers evicted. A model that fits
with nothing to spare behaves nothing like one that misses by 5 GB. See
[What partial offload costs](partial-offload.md).

## 10. Computing every parameter buys one thing

Gemma-4-31B is dense: all 31 billion parameters work on every token.
Gemma-4-26B-A4B is the same family and size, but uses about 4 billion per
token. That is roughly eight times the arithmetic for the same amount of
memory.

| | 26B-A4B | 31B dense | 26B-A4B | 31B dense |
|---|---:|---:|---:|---:|
| Engine | llama.cpp | llama.cpp | vLLM | vLLM |
| Classification F1 | 0.871 | 0.877 | 0.875 | 0.883 |
| Comprehension | 0.884 | **0.916** | 0.873 | **0.914** |
| Translation chrF++ | 56.12 | 56.38 | 55.80 | 56.01 |
| Coding pass rate | **0.834** | 0.826 | 0.826 | 0.828 |
| Classification, sentences/s | **8.94** | 2.24 | **51.13** | 18.18 |

**Three of the four scores do not move.** F1, translation and coding all differ
by less than the 0.02 this study treats as noise, and coding goes the wrong way
on llama.cpp. Only comprehension gains, by about 0.03 on both engines — the same
place where the small model lost most in finding 7, and for the same reason.

**The cost is 3 to 4 times the wall time.** 456 seconds becomes 1 823 on
llama.cpp; 80 becomes 224 on vLLM. Generation drops from 101.9 tokens per second
to 25.5.

**Batching still works.** From [throughput.md](throughput.md), sentences at 1
and 64 requests: the dense model goes 2.9 to 47.8, a gain of 16.4×, the largest
in the table. Being dense costs throughput per request; it does not stop the
engine filling the card with more of them.

So the cost is what it looks like: three to four times the wall time, paid
evenly, for one measurable gain in comprehension.

## Choosing

| Workload | Choice | Why |
|---|---|---|
| Batched multilingual bulk, short prompts | Gemma-4-26B-A4B on vLLM | 0.875 F1 at 51 sentences/s, and 13.9× from concurrency |
| The same work on whole documents | Gemma-4-26B-A4B on vLLM | still the fastest, but expect 13 articles a second, not 120 — concurrency buys 1.4× on long prompts, for every model here |
| Highest quality, speed secondary | Qwopus3.6-27B-Coder on vLLM | 0.906 F1 and 0.915 comprehension, at a third of the throughput |
| One request at a time | any model on llama.cpp | answering while vLLM is still starting |
| Agent prompt-reading | Qwen3-Coder-30B-A3B | fastest prefill; keep it away from prose |
| Already running Qwen3.6-35B | change engine before changing model | 13× the throughput under load, for 0.006 F1 |

## What this does not tell you

- **One run per cell.** No error bars. Differences under 0.02 F1 are noise.
- **Single-turn only.** No agent loops, no long conversations.
- **Twenty languages.** Nothing about low-resource languages, where models
  differ far more.
- **Quality was measured at an 8 192-token context**, latency and the long-form
  ladder at 32 768. Both are stated where they apply.
