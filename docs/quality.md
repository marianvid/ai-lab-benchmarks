# Quality

Four tasks, one pass each, across 10 model and engine combinations.
Each table gives the score and the time it took; both came out of the
same run.

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
| Gemma-4-31B | llama.cpp | **0.877** | 0.960 | 2.24 | 165.8 | 1823.0 s |
| Gemma-4-31B | vLLM | **0.883** | 0.962 | 18.18 | 1350.4 | 224.4 s |
| Gemma-4-E4B | llama.cpp | **0.828** | 0.945 | 11.62 | 851.2 | 351.22 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.726** | 0.933 | 49.9 | 4756.3 | 81.76 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.895** | 0.969 | 8.03 | 626.1 | 507.86 s |
| Qwen3.6-35B-A3B | vLLM | **0.889** | 0.967 | 53.6 | 4507.8 | 76.11 s |
| Qwopus3.6-27B-Coder | vLLM | **0.906** | 0.971 | 19.69 | 1531.0 | 207.2 s |

**Accuracy is higher than F1 for every model, and the gap matters.**
Only 15% of the sentences are political, so a model answering "no" to
everything scores 0.85 accuracy and finds nothing. F1 collapses in that
case; accuracy does not. Judge by F1.

**Prefill here is not a long-prompt figure.** These are single sentences
sent five to a request, a few hundred tokens each. For prompt reading at
8 000 and 29 000 tokens see [latency.md](latency.md).

**Wall time here is not a quality signal.** It is the same work, but
llama.cpp ran it with eight requests in flight and gained nothing from
that; see [throughput.md](throughput.md).

## Comprehension

A passage, a question about it, four answers of which one is right. The
model replies with a single letter. 100 questions per language, 2 000 in
total, always the same 100 so every model is asked the same things.

| Model | Engine | [Accuracy](glossary.md#accuracy "fraction answered correctly, 0-1") | [Unanswered](glossary.md#unanswered "requests that produced no usable answer, out of 2 000. Counted as wrong, not dropped") | Questions/s | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.742** | 0 | 32.97 | 60.66 s |
| Gemma-4-26B-A4B | llama.cpp | **0.884** | 43 | 9.45 | 207.13 s |
| Gemma-4-26B-A4B | vLLM | **0.873** | 43 | 59.08 | 33.13 s |
| Gemma-4-31B | llama.cpp | **0.916** | 12 | 2.07 | 961.76 s |
| Gemma-4-31B | vLLM | **0.914** | 11 | 25.89 | 76.83 s |
| Gemma-4-E4B | llama.cpp | **0.760** | 0 | 18.12 | 110.35 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.847** | 0 | 59.54 | 33.59 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.913** | 2 | 4.33 | 461.76 s |
| Qwen3.6-35B-A3B | vLLM | **0.895** | 0 | 30.53 | 65.51 s |
| Qwopus3.6-27B-Coder | vLLM | **0.915** | 0 | 19.92 | 100.41 s |

**Guessing scores 0.25**, because there are four options. Subtract it
before comparing: 0.74 and 0.91 are not 23% apart, they are 0.49 and
0.66 above chance, which is a third more.

**This is where model size shows.** The smallest model loses far more
here than on classification or coding. A passage has to be understood;
it cannot be pattern-matched from a keyword.

**Unanswered questions are counted as wrong.** The answer is read from
the first eight tokens, and a model that writes anything other than a
letter there has not answered. The score divides by all 2 000, so a
model that fails to answer is penalised exactly as much as one that
answers incorrectly — no model is flattered by the questions it skipped.

**It is the two large Gemma models, on either engine.** Gemma-4-26B-A4B
loses 43 both times; Gemma-4-31B loses 12 and 11. The same model loses
about the same number whichever engine runs it, which puts the cause in
the weights rather than in the engine or the harness. Gemma-4-E4B, the
small one, loses none, and nothing else in the table loses more than 2.

**They are a few questions, not a scatter.** The harness now records
which question produced no letter and what came back instead. For
Gemma-4-31B on llama.cpp the 12 misses are three questions: number 48 in
nine languages, number 24 in two, and number 89 in one. See
[the recorded misses](../results/gemma31-gguf-comprehension-misses.json).

**What came back was an explanation rather than a letter.** On question
48 the model began "The provided passage lists ..."; on 24 and 89,
"None of the options are correct based on ...". Question 48 asks which
of four activities does not reflect personal involvement, and none of
the four appears anywhere in its passage.

The system prompt tells the model the answer is always in the passage
and not to object that it is incomplete. On these questions it objects
anyway, the objection is cut off at eight tokens, and the score counts
it wrong. That is a measurement of instruction-following, not of
comprehension. Only Gemma-4-31B on llama.cpp has this recorded — the
other runs predate the change and have counts only.

## Translation

English into 19 languages, 50 sentences each, 950 translations per
model, scored against FLORES's human translations.

| Model | Engine | [chrF++](glossary.md#chrf "0-100, higher better. Overlap with a human reference translation, counted in character sequences") | Translations/s | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **50.39** | 7.11 | 133.63 s |
| Gemma-4-26B-A4B | llama.cpp | **56.12** | 2.71 | 350.82 s |
| Gemma-4-26B-A4B | vLLM | **55.80** | 11.59 | 81.96 s |
| Gemma-4-31B | llama.cpp | **56.38** | 0.74 | 1285.08 s |
| Gemma-4-31B | vLLM | **56.01** | 5.05 | 188.12 s |
| Gemma-4-E4B | llama.cpp | **54.08** | 3.35 | 283.69 s |
| Qwen3-Coder-30B-A3B | vLLM | **45.38** | 8.25 | 115.15 s |
| Qwen3.6-35B-A3B | llama.cpp | **54.24** | 1.93 | 492.87 s |
| Qwen3.6-35B-A3B | vLLM | **53.79** | 9.65 | 98.49 s |
| Qwopus3.6-27B-Coder | vLLM | **52.99** | 5.03 | 188.89 s |

**The values are low because the language mix is hard.** These 19
include Tamil, Thai, Bengali and Lithuanian. A study covering only
western European languages reports ten to fifteen points higher for the
same models. Compare within this table only.

**The references were made by people**, not generated. A score here is
agreement with a human translator rather than with another model.

## Coding

541 Python problems. The generated code is executed against the tests
that came with the problem; it passes or it does not.

| Model | Engine | [Pass rate](glossary.md#pass-rate "fraction of problems whose generated code ran and passed every test") | Passed | HumanEval+ | MBPP+ | [Wall](glossary.md#wall--wall-time "seconds on a clock, start to finish") |
|---|---|---:|---:|---:|---:|---:|
| GLM-4.7-Flash | vLLM | **0.706** | 382/541 | 0.749 | 0.688 | 203.94 s |
| Gemma-4-26B-A4B | llama.cpp | **0.834** | 451/541 | 0.951 | 0.783 | 688.64 s |
| Gemma-4-26B-A4B | vLLM | **0.826** | 447/541 | 0.945 | 0.775 | 219.86 s |
| Gemma-4-31B | llama.cpp | **0.826** | 447/541 | 0.939 | 0.778 | 1847.28 s |
| Gemma-4-31B | vLLM | **0.828** | 448/541 | 0.945 | 0.778 | 349.47 s |
| Gemma-4-E4B | llama.cpp | **0.765** | 414/541 | 0.877 | 0.717 | 674.73 s |
| Qwen3-Coder-30B-A3B | vLLM | **0.791** | 428/541 | 0.890 | 0.749 | 153.6 s |
| Qwen3.6-35B-A3B | llama.cpp | **0.808** | 437/541 | 0.902 | 0.767 | 486.95 s |
| Qwen3.6-35B-A3B | vLLM | **0.810** | 438/541 | 0.902 | 0.770 | 147.69 s |
| Qwopus3.6-27B-Coder | vLLM | **0.815** | 441/541 | 0.932 | 0.765 | 304.9 s |

**HumanEval+ scores higher than MBPP+ for every model.** HumanEval gives
the function signature and a docstring to complete; MBPP describes the
task in one sentence and pins the function name only through an example
call. Less structure, more room to misread it.

**These problems are in every model's training data.** They are old and
public, so part of a score is memory rather than reasoning. That would
invalidate a ranking of programmers; here they are a fixed, executable
workload for measuring the configuration.

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
| Gemma-4-31B (llama.cpp) | 0.88 | 0.89 | 0.91 | 0.87 | 0.88 | 0.88 | 0.87 | 0.85 | 0.89 | 0.89 | 0.85 | 0.87 | 0.88 | 0.88 | 0.84 | 0.88 | 0.88 | 0.90 | 0.90 | 0.85 |
| Gemma-4-31B (vLLM) | 0.88 | 0.89 | 0.91 | 0.88 | 0.84 | 0.88 | 0.87 | 0.84 | 0.89 | 0.89 | 0.90 | 0.88 | 0.88 | 0.88 | 0.90 | 0.88 | 0.88 | 0.90 | 0.90 | 0.89 |
| Gemma-4-E4B (llama.cpp) | 0.88 | 0.75 | 0.83 | 0.83 | 0.86 | 0.85 | 0.80 | 0.80 | 0.83 | 0.84 | 0.83 | 0.79 | 0.77 | 0.80 | 0.86 | 0.85 | 0.80 | 0.82 | 0.88 | 0.88 |
| Qwen3-Coder-30B-A3B (vLLM) | 0.73 | 0.64 | 0.72 | 0.76 | 0.77 | 0.77 | 0.65 | 0.64 | 0.69 | 0.72 | 0.68 | 0.73 | 0.72 | 0.67 | 0.73 | 0.73 | 0.72 | 0.80 | 0.80 | 0.81 |
| Qwen3.6-35B-A3B (llama.cpp) | 0.92 | 0.90 | 0.88 | 0.92 | 0.94 | 0.87 | 0.87 | 0.87 | 0.92 | 0.86 | 0.89 | 0.87 | 0.88 | 0.88 | 0.92 | 0.89 | 0.90 | 0.90 | 0.92 | 0.92 |
| Qwen3.6-35B-A3B (vLLM) | 0.90 | 0.83 | 0.88 | 0.90 | 0.94 | 0.92 | 0.88 | 0.89 | 0.92 | 0.84 | 0.89 | 0.90 | 0.88 | 0.88 | 0.79 | 0.87 | 0.90 | 0.92 | 0.92 | 0.92 |
| Qwopus3.6-27B-Coder (vLLM) | 0.92 | 0.92 | 0.91 | 0.92 | 0.91 | 0.92 | 0.91 | 0.90 | 0.92 | 0.91 | 0.88 | 0.94 | 0.95 | 0.89 | 0.83 | 0.88 | 0.94 | 0.89 | 0.94 | 0.88 |

A model can look competent on the average and be much weaker in one
language. Read down a column rather than across a row.

With about 30 positive examples per language, one misjudged sentence
moves that language's F1 by roughly 0.015. Gaps under 0.03 between
languages are noise.
