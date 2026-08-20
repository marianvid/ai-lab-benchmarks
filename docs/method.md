# Method

Six measurements were done. Every task records both a score and a rate, from the same pass. Terms used in
the tables are explained in the [glossary](glossary.md).

## Where the data comes from

Nothing is stored in this repository. `harness/get_datasets.py` downloads the
four evaluation sets from their location and writes a manifest
listing what came from where, under which licence.

| Set | Source | Licence |
|---|---|---|
| FLORES-200 | `dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz` | CC BY-SA 4.0 |
| SIB-200 | `huggingface.co/datasets/Davlan/sib200` | CC BY-SA 4.0 |
| Belebele | `huggingface.co/datasets/facebook/belebele` | CC BY-SA 4.0 |
| HumanEval+ / MBPP+ | `huggingface.co/datasets/evalplus/*` | Apache 2.0 |

Three of them share a foundation. SIB-200 and Belebele are both built on FLORES
passages, so a model is classifying, understanding and translating the same
sentences. That is why a weakness in one language tends to show up in all three
at once.

## Languages

Twenty: English, Chinese, Hindi, Spanish, Arabic, French, Bengali, Portuguese,
Russian, Japanese, German, Korean, Turkish, Vietnamese, Tamil, Thai, Polish,
Ukrainian, Romanian and Lithuanian.

They cover ten writing systems — Latin, Han, Devanagari, Arabic, Bengali,
Japanese, Hangul, Tamil, Thai and Cyrillic — which turns out to matter less than
it sounds. See [tokenizer cost](tokenizer.md).

## 1. Classification

`bench_classify.py`, using SIB-200.

The model is shown a sentence and asked one yes-or-no question: is this about
politics? The set is unbalanced so that a model cannot do well by answering "no" to everything.

All 4 080 sentences of the test split are used, in all twenty languages. They go
five to a request, so 816 requests, sent at whatever concurrency the run
specifies.

Out of it comes an F1 score overall and one per language, along with sentences
per second and the token rates.

When a language slice happens to contain no political sentences at all, its F1
is reported as undefined rather than as 0.0. There was nothing to find, so a
score of zero would say the model failed at something it was never asked.

## 2. Comprehension

`bench_comprehension.py`, using Belebele.

The model reads a passage, then a question about it, then four possible answers,
and replies with a single letter.

The first 100 questions of each language are used, 2 000 in all. Always the
first hundred and never a random sample, so every model is asked exactly the
same things and the scores can go in one table.

Four options mean that guessing scores 0.25. A result near that says the model
did not read the passage.

The answer is read from the first eight tokens. A reply with no A, B, C or D in
it counts as wrong — the score divides by all 2 000, so nothing is dropped. The
question and what came back instead are written to the result file, under
`misses`, so a count can be looked into rather than guessed at.

## 3. Translation

`bench_translate.py`, using FLORES-200.

English into the other nineteen languages, the first 50 sentences of the test
split each, so 950 translations per model. The reference is FLORES's own
translation, made by a professional translator.

Scoring is chrF++ from `sacrebleu`, which compares the model's output with that
reference by counting shared character sequences. No second model is involved in
judging.

Two cheap checks run alongside, because a reasonable-looking score can hide a
disaster. One counts English function words left in the output; the other
compares the digits in the source with the digits in the translation.

Both are weak signals rather than scores. Most of the English-word hits turn out
to be organisation names correctly left in English. They are there to point at
translations worth reading, not to rank anything. Digit group separators are
removed before comparing, because `4,475` legitimately becomes `4 475` in some
languages.

## 4. Coding

`bench_coding.py`, using HumanEval+ and MBPP+.

541 problems, of two shapes. HumanEval gives a function signature and a
docstring to complete:

```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each
    other than given threshold. """
```

MBPP describes the task in a sentence and pins the function's name through one
example call:

> Write a function to find the shared elements from the given two lists.
>
> `assert set(similar_elements((3, 4, 5, 6), (5, 7, 4, 10))) == set((4, 5))`

Whatever the model writes is pulled out of its code block, joined to the tests
that came with the problem, and run. It passes or it does not. Nothing is graded
by opinion and there are no partial marks.

One problem, HumanEval/32, is left out because its own reference solution fails
its own tests. All 164 reference solutions were run through this harness to
check that the harness itself was sound: 163 of them pass.

The generated code runs as user `nobody` when the harness has root to drop from,
in a throwaway directory, with a thirty-second limit. The interpreter it runs
under has numpy, scipy and sympy installed, because several of the EvalPlus
tests import them and without them those problems would fail for a reason that
has nothing to do with the model.

## 5. Latency

`bench.py`. No evaluation set — the prompt is generated.

One request at a time, at three sizes: roughly 500, 9 000 and 29 000 tokens. The
prompt is a chunk of Python source repeated until it reaches the length wanted,
followed by a request to rewrite one of the functions. That is the shape of an
agent pasting a codebase into every turn.

It reports time to first token, the prompt-reading rate and the generation rate
at each size. This is the only place in the repository where long prompts are
sent to a model.

The longest prompt is 29 000 tokens rather than 32 000 because the prompt and
the answer share the [context window](glossary.md#context-window). With the
window set to 32 768, a 33 000-token prompt plus a 256-token answer does not fit,
and every model refuses it with an HTTP 400.

## 6. Long-form throughput

`bench_longform.py`, using whole Wikipedia articles.

Sixty articles per run, between 2 165 and 5 227 characters, in six languages.
Each one is sent complete, with a request for a one-word subject label. Long
input, short output — the shape of classification, routing or tagging work on
real documents.

**Nothing is marked here.** The answers are never checked against anything. What
is being measured is articles per second and tokens per second at 1, 8, 32 and
64 requests in flight.

It exists because every other task in this suite sends a sentence or a short
passage, and prompt length changes how an engine behaves: the prompt is what
fills the [KV cache](glossary.md#kv-cache), and the cache is what limits how
many requests fit at once. The two ladders turn out to disagree — see
[throughput](throughput.md).

`harness/fetch_wikipedia.py` collects the articles. The text is CC BY-SA 4.0 and
every row keeps its page id, revision id and URL, so each article stays
attributable.

## Loading

Each model is loaded twice in a row. The first time the file is not in memory;
the second follows immediately, with the file still in the operating system's
page cache.

The host's page cache is emptied before the run starts, so the first load of the
first model is genuinely cold.

## Rules that apply everywhere

**A warm-up pass is run and thrown away.** The first pass after an engine starts
is about 40% slower than the rest while its kernel autotuning settles. Measuring
that would be measuring the wrong thing. The coding task is the exception: every
problem there is different, so a discarded pass would throw away real answers.

**Reasoning is switched off where the engine allows it.** The request carries
`chat_template_kwargs: {enable_thinking: false}`, and if the engine answers 400
or 422 it is sent again without that argument — not every engine and model
accepts it. If a model writes out its thinking anyway, the `<think>` block is
stripped before the answer is marked.

**Temperature is 0** everywhere.

**One model on the card at a time.** There is one 32 GB card; there is no
alternative.

**Failures are recorded, not hidden.** A model that will not start, a request
that times out, a test that crashes — each appears in the result files as a
fact.

## How a run is orchestrated

`harness/run_all.py` takes each model in turn: loads it through AI-Lab, waits
until it answers, loads it a second time for the warm figure, then runs the four
quality tasks, the short-prompt concurrency ladder, the latency test and the
long-form ladder, and unloads.

`summary.json` is written after every model, so a run killed halfway still
leaves everything that finished. A model that will not load is recorded and the
run carries on to the next one.

`harness/make_report.py` turns `results/` into the result pages. The tables
there are generated rather than typed, so every number can be traced back to the
file it came from.
