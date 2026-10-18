<!-- throughput_intro -->
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

<!-- short_notes -->

**Gain is the highest rate divided by the lowest**: what the engine got
out of being handed more work at once. A gain of 1.0 means nothing — the
ninth request waited for one of the first eight to finish.

**At one request at a time the engines are comparable.** The difference
appears only under load, from
[continuous batching](glossary.md#continuous-batching).

**vLLM stops improving between 32 and 64**: the card is saturated, and
further requests only wait longer.

<!-- long_heading -->
## Long prompts — whole articles

The same ladder, sending complete Wikipedia articles and asking for a
one-word answer. Long input, short output: the shape of
classification, routing and tagging work on real documents. 60
articles per run, 2 165–5 227 characters, six languages.

<!-- long_notes -->

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

<!-- prefill_heading -->
## Prompt reading as concurrency rises

The same long-prompt runs, reporting prompt reading rather than
articles finished. ${prefill}.

<!-- prefill_notes -->

**A prefill rate needs the concurrency it was measured at.** On
vLLM, reading eight articles together is 1.2× to 1.4× faster per
token than reading one; past eight it stops improving. On
llama.cpp the figure does not move at all.

These are aggregate rates — every prompt token in the run divided
by the wall clock — so they say how much text the card gets
through, not how quickly any one request is answered. For that,
see [latency.md](latency.md).

<!-- latency_intro -->
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

<!-- latency_notes -->
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
