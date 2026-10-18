<!-- intro -->
Four tasks, one pass each, across ${complete} complete model and engine combinations. ${partial} newer combinations currently have coding-only results.
Each table gives the score and the time it took; both came out of the
same run.

See [method.md](method.md) for how each task was run and
[models.md](models.md) for what the models are.

<!-- how_to_read -->
## How to read these tables

Every table has two kinds of column. The **score** says how well the
model did; the **rate** and the **time** say how fast. They are
independent — the fastest model here is not the most accurate one.

| Column | What it measures | Range | Better |
|---|---|---|---|
| F1 | classification, balancing the ones it found against the ones it got right | 0 to 1 | higher |
| Accuracy | the fraction of questions answered correctly | 0 to 1 | higher |
| chrF++ | how much a translation overlaps a human one, counted in character sequences | 0 to 100 | higher |
| Pass rate | the fraction of programs that ran and passed every test | 0 to 1 | higher |
| HumanEval+, MBPP+ | the pass rate on each half of the coding set | 0 to 1 | higher |
| Passed | problems passed, out of 541 | a count | higher |
| Unanswered | questions that got no usable reply, out of 2 000 | a count | lower |
| Sentences/s, Questions/s, Translations/s | items finished per second | per second | higher |
| Prefill | how fast the model reads a prompt | tokens per second | higher |
| Wall | how long the whole task took | seconds | lower |

**A score near the bottom of its range is not a bad model, it is a
hard task.** Comprehension is a choice between four answers, so 0.25
is what guessing scores and the useful range starts there. Translation
scores are held down by the languages in the set; see the caveat in
the [README](../README.md).

<!-- classification -->
## Classification

The model reads a sentence and answers one question: is its topic
politics. 4 080 sentences in 20 languages, of which 15% are political.

<!-- classification_notes -->

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

<!-- comprehension -->
## Comprehension

A passage, a question about it, four answers of which one is right. The
model replies with a single letter. 100 questions per language, 2 000 in
total, always the same 100 so every model is asked the same things.

<!-- comprehension_notes -->

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

<!-- gemma_misses -->
**It is the two large Gemma models, on either engine.** Gemma-4-26B-A4B
loses 43 both times; Gemma-4-31B loses 12 and 11. The same model loses
about the same number whichever engine runs it, which puts the cause in
the weights rather than in the engine or the harness. Gemma-4-E4B, the
small one, loses none, and nothing else in the table loses more than 2.

**They are the same few questions, asked in different languages.** The
harness records what came back when no letter did. Nine of the twelve
misses by Gemma-4-31B on llama.cpp are one question, translated: it
asks which of four activities does not reflect personal involvement,
and none of the four is mentioned anywhere in the passage it is asked
about. Instead of guessing, the model started explaining — "The
provided passage lists ..." — and ran out of room. The other three are
two questions where it answered "None of the options are correct".

The system prompt tells it the answer is always in the passage and not
to object that it is incomplete. On these questions it objects anyway,
the objection is cut off at eight tokens, and the score counts it
wrong. Part of this column therefore measures whether a model does as
it is told, not whether it understood. Only Gemma-4-31B on llama.cpp
has the detail recorded — the other runs predate the change and have
counts only.

<!-- translation -->
## Translation

English into 19 languages, 50 sentences each, 950 translations per
model, scored against FLORES's human translations.

<!-- translation_notes -->

**The values are low because the language mix is hard.** These 19
include Tamil, Thai, Bengali and Lithuanian. A study covering only
western European languages reports ten to fifteen points higher for the
same models. Compare within this table only.

**The references were made by people**, not generated. A score here is
agreement with a human translator rather than with another model.

<!-- coding -->
## Coding

541 Python problems. The generated code is executed against the tests
that came with the problem; it passes or it does not.

<!-- coding_notes -->

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

<!-- languages_intro -->
## Classification, language by language

The same run as the classification table above, taken apart by the
language the sentence was written in. Nothing extra was measured: those
4 080 sentences are 204 in each of twenty languages, and this is the
score for each group of 204 on its own.

**Every cell is an F1 score for one model in one language**, on the same
question as before — is this sentence about politics. 0 to 1, higher is
better. About 30 of each language's 204 sentences are political.

The columns are language codes: ar Arabic, bn Bengali, de German, en
English, es Spanish, fr French, hi Hindi, ja Japanese, ko Korean, lt
Lithuanian, pl Polish, pt Portuguese, ro Romanian, ru Russian, ta Tamil,
th Thai, tr Turkish, uk Ukrainian, vi Vietnamese, zh Chinese.

It answers one question: does a model that scores well overall do so
everywhere, or does the average hide a language it is bad at.

<!-- languages_notes -->

**Across a row** to see whether one model is weaker in some languages
than others. Qwopus3.6-27B has the best average in the table above and
still drops to 0.83 on Tamil, where Qwen3.6-35B on llama.cpp reaches
0.92 — and where the same Qwen3.6-35B on vLLM manages only 0.79.

**Down a column** to see whether a low score is the model or the
language. If every model drops in the same column, the language is the
hard part and no model choice will fix it.

With about 30 positive examples per language, one misjudged sentence
moves that language's F1 by roughly 0.015. Gaps under 0.03 between
languages are noise.
