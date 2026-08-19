# What it means

What follows from the numbers in `02-results.md`, for someone deciding how to
use a machine like this one.

## The short version

**The engine is a bigger decision than the model.**

The same model, the same weights, measured on both engines:

| | Quality (F1) | Sentences/s | |
|---|---:|---:|---|
| Gemma-4-26B-A4B on llama.cpp | 0.871 | 8.9 | |
| Gemma-4-26B-A4B on vLLM | 0.875 | **51.1** | **5.7× the work** |
| Qwen3.6-35B-A3B on llama.cpp | 0.895 | 8.0 | |
| Qwen3.6-35B-A3B on vLLM | 0.889 | **53.6** | **6.7× the work** |

**The quality is the same. The throughput is not.** Within noise on the answers,
six times the work per hour.

## The five things worth knowing

### 1. Continuous batching is still the largest effect

Not quantisation, not model choice, not the card's native number formats.

| Engine | Throughput gain, concurrency 1 → 64 |
|---|---|
| vLLM | **7.1× to 19.6×** |
| llama.cpp | **1.0× to 1.1×** |

llama.cpp does not get faster when you send it more work. It has a fixed number
of slots and divides the context window among them. vLLM keeps a shared pool and
interleaves requests continuously, so a request that finishes early frees
capacity at once.

**When this does not apply:** if you send one request at a time, the advantage
mostly disappears — and llama.cpp starts far faster, 3 to 11 seconds against 45
to 98. For a model you load, ask one question, and unload, llama.cpp wins on the
clock that matters.

### 2. A coding model is the wrong tool for language

Qwen3-Coder-30B-A3B reads prompts faster than anything else measured. It is also
last at every language task, by a distance:

| | Best | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | **0.726** |
| Translation chrF++ | 56.12 | **45.38** |
| Comprehension | 0.915 | 0.847 |

It is not a bad model. It is a model built for a different job, and the numbers
say so clearly enough that the mistake is worth avoiding on purpose.

### 3. Size buys much less than expected

Gemma-4-E4B is **4.6 GB**. The best model in the set is more than five times
larger.

| | 4.6 GB model | Best measured |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding pass rate | 0.765 | 0.834 |
| Comprehension | 0.760 | 0.915 |

It loads in **3.3 seconds**. For work where a wrong answer is cheap and volume
is high, the small model is not a compromise so much as a different trade.

Comprehension is where size actually shows: 0.760 against 0.915 is a real gap,
and it is the test that cannot be bluffed.

### 4. Prompt reading and generation are separate problems

They do not move together, and a machine can be good at one and ordinary at the
other. Prompt reading is done in parallel and reaches thousands of tokens per
second; generation is one token after another and reaches tens.

Which one matters depends entirely on the work. An agent that re-reads a
codebase at every step lives or dies on prompt reading. A bulk classifier that
answers "yes" or "no" barely generates anything at all.

### 5. A context window is worth less in some languages, and not the ones you would guess

The same sentences, counted by the same tokenizer:

| | Tokens, against English |
|---|---:|
| Chinese (Han) | 1.12× |
| Japanese | 1.24× |
| Hindi (Devanagari) | 1.31× |
| Russian (Cyrillic) | 1.40× |
| Ukrainian (Cyrillic) | 1.64× |
| Thai | 1.65× |
| **Lithuanian (Latin)** | **1.66×** |

**It is not the writing system.** Chinese, in Han characters, is the cheapest
language measured after English. The most expensive is Lithuanian — written in
the same alphabet as English.

What decides the cost is how well the tokenizer knows the language, not how
exotic it looks. A tokenizer trained mostly on English and Chinese web text
handles Chinese in one token per character-cluster and chops Lithuanian into
fragments.

The practical consequence: **an 8 192-token window holds about 60% as much
Lithuanian as English.** If you size a context window on English documents and
then feed it Baltic or Thai text, it will not fit, and the failure will look
like a model problem rather than an arithmetic one.

### 6. A model larger than the card runs, if you let the engine decide

A 46.2 GB model on a 32 GB card, at **56 tokens per second**, with llama.cpp
choosing the split between card and system memory itself.

Told to put a fixed number of layers on the card, it refuses to fit and dies
trying to allocate 34 GB. **Do not force the split.**

AI-Lab refuses this configuration on purpose, because on a GPU attached over
OCuLink a split model sends every token across the cable. The measurement says
what that decision costs — and 56 tok/s is not nothing.

## Choosing

**For bulk work in many languages: Gemma-4-26B-A4B on vLLM.** 0.875 F1 at 51
sentences per second, and 19.6× more throughput as concurrency rises than at
one request at a time. Nothing else combines that quality with that speed.

**For the best answers, if you can wait: Qwopus3.6-27B-Coder.** Top of both
language tests — 0.906 F1, 0.915 comprehension — at a third of Gemma's
throughput.

**For an agent loop: Qwen3-Coder-30B-A3B**, for prompt reading, and for nothing
that involves prose.

**For one question at a time: llama.cpp**, whatever the model. It is answering
while vLLM is still starting.

**If you are already running Qwen3.6-35B: change engine before you change
model.** It is the best or near-best on every language test in this set. Moving
it from llama.cpp to vLLM multiplies its throughput by 6.7 and costs 0.006 F1.

## What this study does not tell you

**Nothing about long prompts.** These sets are sentences and short passages. The
prompt-reading figures come from a separate latency test, not from these runs.

**Nothing about how models behave over a long agent task.** Every test here is
one request and one answer.

**Nothing about languages outside the twenty.** Especially not low-resource
ones, where the gaps between models are usually much larger.

**These are one run each.** No error bars. Differences smaller than about 0.02
F1 should be read as "the same".
