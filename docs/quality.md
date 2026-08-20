# Quality

Four tasks, one pass each, across eight model and engine combinations.
Every table gives the score and the time it took, because both came out
of the same run.

See [method.md](method.md) for how each task was run and
[models.md](models.md) for what the models are.

## Classification

The model reads a sentence and answers one question: is its topic
politics. 4 080 sentences in 20 languages, of which 15% are political.

| Model | Engine | [F1](glossary.md#f1 "0-1, higher better. Precision and recall combined; used because the set is only 15% positive") | [Accuracy](glossary.md#accuracy "fraction answered correctly, 0-1") | Sentences/s | [Prefill](glossary.md#prefill "prompt reading, tokens per second") | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.819** | 0.941 | 36.97 | 3514.9 | 110.35 s |
| Gemma-4-26B-A4B | llama.cpp | **0.871** | 0.963 | 8.94 | 662.2 | 456.41 s |
| Gemma-4-26B-A4B | vLLM | **0.875** | 0.964 | 51.13 | 3797.8 | 79.79 s |
| Gemma-4-E4B | llama.cpp | **0.828** | 0.945 | 11.62 | 851.2 | 351.22 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.726** | 0.933 | 49.9 | 4756.3 | 81.76 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.895** | 0.969 | 8.03 | 626.1 | 507.86 s |
| Qwen3.6-35B-A3B | vLLM | **0.889** | 0.967 | 53.6 | 4507.8 | 76.11 s |
| Qwopus3.6-27B-Coder | vLLM | **0.906** | 0.971 | 19.69 | 1531.0 | 207.2 s |

**Read the two score columns together.** Accuracy is higher than F1 for
every model, and the gap is the point: only 15% of the sentences are
political, so a model answering "no" to everything scores 0.85 accuracy
while finding nothing. F1 collapses when that happens, which is why it
is the column to judge by.

**Prefill here is not a long-prompt figure.** These are single sentences
sent five to a request, a few hundred tokens each. For prompt reading at
8 000 and 29 000 tokens see [latency.md](latency.md).

**Do not read wall time as engine quality.** It is the same work, but
llama.cpp ran it with eight requests in flight and gained nothing from
that. Why is in [throughput.md](throughput.md).

## Comprehension

A passage, a question about it, four answers of which one is right. The
model replies with a single letter. 100 questions per language, 2 000 in
total, always the same 100 so every model is asked the same things.

| Model | Engine | [Accuracy](glossary.md#accuracy "fraction answered correctly, 0-1") | Questions/s | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.742** | 32.97 | 60.66 s |
| Gemma-4-26B-A4B | llama.cpp | **0.884** | 9.45 | 207.13 s |
| Gemma-4-26B-A4B | vLLM | **0.873** | 59.08 | 33.13 s |
| Gemma-4-E4B | llama.cpp | **0.760** | 18.12 | 110.35 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.847** | 59.54 | 33.59 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.913** | 4.33 | 461.76 s |
| Qwen3.6-35B-A3B | vLLM | **0.895** | 30.53 | 65.51 s |
| Qwopus3.6-27B-Coder | vLLM | **0.915** | 19.92 | 100.41 s |

**Guessing scores 0.25**, because there are four options. Subtract that
before comparing. 0.74 and 0.91 are not a 23% difference in ability:
they are 0.49 and 0.66 above chance, which is a third more.

**This is the task that separates by model size.** The smallest model
loses far more here than on classification or coding. A passage has to
be understood; it cannot be pattern-matched from a keyword.

## Translation

English into 19 languages, 50 sentences each, 950 translations per
model, scored against FLORES's human translations.

| Model | Engine | [chrF++](glossary.md#chrf "0-100, higher better. Overlap with a human reference translation, counted in character sequences") | Translations/s | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **50.39** | 7.11 | 133.63 s |
| Gemma-4-26B-A4B | llama.cpp | **56.12** | 2.71 | 350.82 s |
| Gemma-4-26B-A4B | vLLM | **55.80** | 11.59 | 81.96 s |
| Gemma-4-E4B | llama.cpp | **54.08** | 3.35 | 283.69 s |
| Qwen3-Coder-30B-A3B | vLLM | **45.38** | 8.25 | 115.15 s |
| Qwen3.6-35B-A3B | llama.cpp | **54.24** | 1.93 | 492.87 s |
| Qwen3.6-35B-A3B | vLLM | **53.79** | 9.65 | 98.49 s |
| Qwopus3.6-27B-Coder | vLLM | **52.99** | 5.03 | 188.89 s |

**The absolute values are low because the language mix is hard.** These
19 languages include Tamil, Thai, Bengali and Lithuanian. A study
covering only western European languages reports numbers ten to fifteen
points higher for the same models. Compare within this table only.

**The reference translations were made by people**, which is not true of
every translation benchmark. A score here means agreement with a human
translator rather than with another model.

## Coding

541 Python problems. The generated code is executed against the tests
that came with the problem; it passes or it does not.

| Model | Engine | [Pass rate](glossary.md#pass-rate "fraction of problems whose generated code ran and passed every test") | Passed | HumanEval+ | MBPP+ | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.706** | 382/541 | 0.749 | 0.688 | 203.94 s |
| Gemma-4-26B-A4B | llama.cpp | **0.834** | 451/541 | 0.951 | 0.783 | 688.64 s |
| Gemma-4-26B-A4B | vLLM | **0.826** | 447/541 | 0.945 | 0.775 | 219.86 s |
| Gemma-4-E4B | llama.cpp | **0.765** | 414/541 | 0.877 | 0.717 | 674.73 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.791** | 428/541 | 0.890 | 0.749 | 153.6 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.808** | 437/541 | 0.902 | 0.767 | 486.95 s |
| Qwen3.6-35B-A3B | vLLM | **0.810** | 438/541 | 0.902 | 0.770 | 147.69 s |
| Qwopus3.6-27B-Coder | vLLM | **0.815** | 441/541 | 0.932 | 0.765 | 304.9 s |

**HumanEval+ scores higher than MBPP+ for every model.** HumanEval gives
the function signature and a docstring to complete. MBPP describes the
task in one sentence and pins the function's name only through an
example call — less structure, more room to misread it.

**These problems are in every model's training data.** They are old and
public. That would invalidate a study ranking models by reasoning. It
does not affect this one, which uses them as a fixed, standard,
executable workload for measuring a machine.

**One problem is excluded.** HumanEval/32's own reference solution fails
its own tests. All 164 references were run through this harness to check:
163 pass. Leaving it in would deduct a point from every model for
something none of them can pass.

## Per-language classification scores

The same classification run, split by the language of the sentence. Each
language contributes 204 sentences, about 30 of them political.

| Model | ar | bn | de | en | es | fr | hi | ja | ko | lt | pl | pt | ro | ru | ta | th | tr | uk | vi | zh |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GLM-4.7-Flash (vLLM) | 0.79 | 0.84 | 0.79 | 0.84 | 0.80 | 0.88 | 0.86 | 0.79 | 0.85 | 0.84 | 0.79 | 0.84 | 0.80 | 0.79 | 0.90 | 0.79 | 0.71 | 0.85 | 0.83 | 0.81 |
| Gemma-4-26B-A4B (llama.cpp) | 0.88 | 0.80 | 0.86 | 0.85 | 0.92 | 0.86 | 0.84 | 0.86 | 0.87 | 0.84 | 0.94 | 0.90 | 0.86 | 0.88 | 0.85 | 0.88 | 0.85 | 0.86 | 0.89 | 0.92 |
| Gemma-4-26B-A4B (vLLM) | 0.92 | 0.88 | 0.85 | 0.89 | 0.92 | 0.83 | 0.86 | 0.86 | 0.85 | 0.88 | 0.90 | 0.88 | 0.83 | 0.88 | 0.87 | 0.88 | 0.86 | 0.84 | 0.89 | 0.92 |
| Gemma-4-E4B (llama.cpp) | 0.88 | 0.75 | 0.83 | 0.83 | 0.86 | 0.85 | 0.80 | 0.80 | 0.83 | 0.84 | 0.83 | 0.79 | 0.77 | 0.80 | 0.86 | 0.85 | 0.80 | 0.82 | 0.88 | 0.88 |
| Qwen3-Coder-30B-A3B (vLLM) | 0.73 | 0.64 | 0.72 | 0.76 | 0.77 | 0.77 | 0.65 | 0.64 | 0.69 | 0.72 | 0.68 | 0.73 | 0.72 | 0.67 | 0.73 | 0.73 | 0.72 | 0.80 | 0.80 | 0.81 |
| Qwen3.6-35B-A3B (llama.cpp) | 0.92 | 0.90 | 0.88 | 0.92 | 0.94 | 0.87 | 0.87 | 0.87 | 0.92 | 0.86 | 0.89 | 0.87 | 0.88 | 0.88 | 0.92 | 0.89 | 0.90 | 0.90 | 0.92 | 0.92 |
| Qwen3.6-35B-A3B (vLLM) | 0.90 | 0.83 | 0.88 | 0.90 | 0.94 | 0.92 | 0.88 | 0.89 | 0.92 | 0.84 | 0.89 | 0.90 | 0.88 | 0.88 | 0.79 | 0.87 | 0.90 | 0.92 | 0.92 | 0.92 |
| Qwopus3.6-27B-Coder (vLLM) | 0.92 | 0.92 | 0.91 | 0.92 | 0.91 | 0.92 | 0.91 | 0.90 | 0.92 | 0.91 | 0.88 | 0.94 | 0.95 | 0.89 | 0.83 | 0.88 | 0.94 | 0.89 | 0.94 | 0.88 |

**Averages hide this.** A model can look competent overall and be much
weaker in one language. Read down a column rather than across a row.

With about 30 positive examples per language, one misjudged sentence
moves that language's F1 by roughly 0.015. Treat gaps under 0.03 between
languages as noise.
