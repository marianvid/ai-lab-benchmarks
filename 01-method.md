# Method — what was measured, how, and what the words mean

Four tests, each a script in `harness/`. **The script is the definition of its
test**; this file explains the intent behind it.

Every test reports two things from the same pass: **how well the model did, and
how long it took**. That is deliberate. The question this study asks is not
which model is cleverest — it is how one machine behaves under a given kind of
work, and a score without a clock answers half of it.

## Vocabulary, once

**Prompt reading** — turning the text you send into numbers the model can work
with. It happens once per request and can be done for many tokens at a time, so
it is fast. Also called prefill.

**Generation** — writing the answer, one token at a time, each token depending
on the last. It cannot be parallelised within one request, so it is slow. Also
called decode.

**Concurrency** — how many requests are in flight at once. It is the single
setting that separates the two engines here.

**Continuous batching** — an engine's ability to work on many requests at the
same time, adding and removing them as they arrive and finish. vLLM does this;
llama.cpp divides a fixed number of slots instead.

**F1** — one number combining "of the things it said were X, how many were" and
"of the things that were X, how many it found". Used instead of accuracy
because these sets are unbalanced on purpose. On a set where one item in seven
is a yes, a model that always says no is 86% accurate and useless.

**chrF++** — how much a translation looks like a reference translation, counted
in character sequences. Mechanical: no judge model, no opinion.

## Where the data comes from

**Nothing is redistributed by this repository.** `harness/get_datasets.py`
downloads all four sets from the people who published them and writes a
manifest with their licences. Run it once before anything else.

| Set | What it is | Licence |
|---|---|---|
| **FLORES-200** | The same sentences translated into 200 languages **by people** | CC BY-SA 4.0 |
| **SIB-200** | Those sentences, each labelled by people with one of seven topics | CC BY-SA 4.0 |
| **Belebele** | Reading-comprehension questions over the same passages, four options, one right | CC BY-SA 4.0 |
| **HumanEval+ / MBPP+** | 541 Python problems with test suites large enough to fail plausible wrong answers | Apache 2.0 |

Three of the four are built on the same FLORES passages. That is why a model
can be compared across them: it is understanding, categorising and translating
**the same text**.

## Twenty languages, ten writing systems

English, Chinese, Hindi, Spanish, Arabic, French, Bengali, Portuguese, Russian,
Japanese, German, Korean, Turkish, Vietnamese, Tamil, Thai, Polish, Ukrainian,
Romanian, Lithuanian.

Chosen for reach and for variety of script. The variety is not decoration: the
same sentence costs very different numbers of tokens in Han, Devanagari or
Latin, and tokens are speed, memory and money at once.

## Test 1 — Classification (`bench_classify.py`)

Every sentence in SIB-200's test split, in all twenty languages: 4 080 in
total. The question is one yes-or-no — **is this sentence about politics?** —
and about one sentence in seven is.

Sentences go five to a request, so 816 requests, run at a chosen concurrency.
The same pass yields **quality** (F1 overall and per language) and
**throughput** (sentences per second, prompt and generation tokens per second).
That is the same shape as real bulk work, which is why it is measured that way.

## Test 2 — Comprehension (`bench_comprehension.py`)

Belebele: a passage, a question about it, four answers, exactly one correct.
100 questions per language, always the first 100, so every model is asked the
same questions. 2 000 in total.

**This is the test a model cannot bluff.** Classification can be half-guessed
from a keyword; a translation can score well while being subtly wrong. Here the
model has to have understood a passage, and the marking is one letter.

Guessing scores 0.25. A result near that means the model did not read the
passage, whatever else the number looks like.

## Test 3 — Translation (`bench_translate.py`)

English into the other nineteen languages, 50 sentences each, 950 translations
per model. Scored with chrF++ from `sacrebleu` against **FLORES's human
translations**.

That last point matters. An earlier version of this study scored against
reference translations produced by a model, which meant a good score proved
agreement with another machine. Here it means agreement with a person.

Two mechanical checks run alongside, because a score can hide a disaster:
English left untranslated, and numbers that went missing between source and
output. Both are weak signals meant to find candidates to read, not to score.

## Test 4 — Coding (`bench_coding.py`)

541 Python problems from HumanEval+ and MBPP+. Each answer is pulled out of its
code block, run against the problem's own tests, and passes or does not.
Nothing is graded by opinion.

**Why the "+" sets.** The original HumanEval and MBPP ship three or four tests
per problem — thin enough that wrong solutions pass and most models score near
the top. EvalPlus regenerated the suites with far more cases. The scores drop
and start separating models again.

**Contamination is not the concern here.** These problems are old and are
certainly in every model's training data. That would matter for a study asking
which model reasons best. This one asks how a machine behaves, so what matters
is that the work is real, standard, and identical for every model.

**One problem is excluded**: HumanEval/32, whose own reference answer fails its
own tests. Running all 164 reference answers through this harness gives 163
passes and that one failure, so leaving it in would take a point off every model
for something none of them can pass. The exclusion is in the code, with the
reason.

Generated code runs as `nobody`, in a throwaway directory, with a timeout. It is
still someone else's code executing on your machine: run this in a container.

## Rules that apply to every test

**A warm-up pass is thrown away.** The first pass after an engine starts runs
about 40% slow while its kernel autotuning settles. Measuring that measures the
wrong thing. The coding test is the exception: every problem is different, so a
discarded pass would throw away real answers.

**Reasoning is switched off** where the engine allows it, and any scratch work
the model writes anyway is stripped before marking. A model that thinks out
loud and then answers correctly should not be marked wrong for the thinking.

**Temperature is 0** everywhere.

**One model on the card at a time.** It is one 32 GB card; there is no
alternative.

**Failures are recorded, not hidden.** A model that will not start, a test that
crashes, a request that times out — each appears in the results as a fact.
