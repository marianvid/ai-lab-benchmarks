# What partial offload costs

When a model does not fit in VRAM, llama.cpp can keep some layers on the card
and the rest in system memory. It works, and the cost is not evenly distributed:
prompt reading collapses, generation barely moves.

**From the August 2026 study.** GGUF Q4 on llama.cpp, prompts of about 8 000
tokens, on the same 32.6 GB card. The F1 column comes from that study's
classification set, not from [quality.md](quality.md), so it is not comparable
with the scores there. Single runs.

## The Coder-Next family, from 40B to 80B

The same model pruned to four sizes, plus the original.

| Model | Size | Where it sits | Prefill | Generation | TTFT @32k | F1 |
|---|---:|---|---:|---:|---:|---:|
| REAP-40B | 28.5 GB | entirely on the card | **3 126** | 107 | 6.6 s | 0.864 |
| REAP-48B | 33.4 GB | 4 layers in RAM | 1 253 | 80 | 16.1 s | 0.900 |
| REAP-60B | 40.9 GB | 14 layers in RAM | 541 | 56 | 35.4 s | 0.931 |
| 80B, unpruned | 47 GB | 20 layers in RAM | 328 | **54** | 61.3 s | **0.957** |

Speeds are tokens per second.

## Prefill collapses, generation does not

From 40B to 80B, prompt reading falls **9.5×** — 3 126 to 328 tokens per second.
Generation falls **2×** — 107 to 54.

The 80B model, less than half of which is on the card, still writes at 54 tokens
per second. That is usable. It needs a full minute to read a large prompt, which
is not.

The two phases are limited by different things:

**Prompt reading processes the whole prompt at once.** Every layer sitting in
system memory has to have the entire batch of activations sent to it and back,
so layers on the CPU slow it down out of all proportion.

**Generation produces one token at a time** and is limited by memory bandwidth.
On a mixture-of-experts model only a small fraction of the parameters is active
for any given token, so much of what sits in system memory is not touched.

## The cliff is at the first layer that does not fit

Between 28.5 GB and 33.4 GB — four layers moved off the card — prefill drops
**60%**, from 3 126 to 1 253.

That is not a gentle slope. The first layers to be evicted cost the most, and a
model that fits with nothing to spare behaves completely differently from one
that misses by 5 GB.

## Quality runs the other way

F1 rises monotonically with size: 0.864, 0.900, 0.931, 0.957. The unpruned 80B
was the best judge in that whole study, and the least pleasant thing to use.

The pruned variants are the worst of both: slower than a model in a native
format and less accurate than the original they came from. Nothing in that study
recommended them.

## For scale, on the same card

Qwen3-Coder-30B-A3B in NVFP4, which fits entirely: **18 602 tokens per second**
of prompt reading, first token at 32 000 tokens in **3.0 seconds**.

Against the 80B in partial offload, that is 57× the prompt-reading rate and 20×
faster to the first token.

## What follows from it

**Fitting entirely in VRAM is worth more than parameters.** A model that fits
and is quantised to a native format beats a larger one spilling into system
memory, on everything except the score.

**Check whether it fits with room to spare, not just whether it fits.** The
difference between 28.5 GB and 33.4 GB on this card is 60% of prompt reading.

**Partial offload is usable for generation-heavy work only.** Long prompts are
where it fails, and long prompts are what agents send.
