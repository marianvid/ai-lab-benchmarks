# Method

Each script in `harness/` is the definition of its task. This file records the
parameters and the rules.

Every task reports score and throughput from the same pass.

## Terms

**Prefill / prompt reading** — encoding the input. Parallel across tokens,
thousands of tok/s.

**Decode / generation** — producing output tokens serially, tens of tok/s.

**Concurrency** — requests in flight simultaneously.

**Continuous batching** — adding and retiring requests within a running batch.
vLLM does this; llama.cpp uses fixed slots with the context window divided
between them.

**F1** — used instead of accuracy because the classification set is 15%
positive. An always-negative classifier scores 0.85 accuracy, 0.00 F1.

**chrF++** — character n-gram F-score with word bigrams, `sacrebleu`
implementation, no judge model.

## Data

`harness/get_datasets.py` fetches all four sets and writes `MANIFEST.json` with
licences. Nothing is redistributed by this repository.

| Set | Source | Licence |
|---|---|---|
| FLORES-200 | `dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz` | CC BY-SA 4.0 |
| SIB-200 | `huggingface.co/datasets/Davlan/sib200` | CC BY-SA 4.0 |
| Belebele | `huggingface.co/datasets/facebook/belebele` | CC BY-SA 4.0 |
| HumanEval+ / MBPP+ | `huggingface.co/datasets/evalplus/*` | Apache 2.0 |

SIB-200 and Belebele are built on FLORES passages, so the same text is
classified, comprehended and translated.

The HuggingFace copies of FLORES require an account; the Meta tarball does not,
which is why it is fetched from there.

## Languages

en, zh, hi, es, ar, fr, bn, pt, ru, ja, de, ko, tr, vi, ta, th, pl, uk, ro, lt.

Ten scripts: Latin, Han, Devanagari, Arabic, Bengali, Japanese, Hangul, Tamil,
Thai, Cyrillic.

## Task 1 — Classification (`bench_classify.py`)

SIB-200 test split, all 20 languages, 4 080 sentences. Binary: is the topic
`politics`. 15% positive.

5 sentences per request → 816 requests at the given concurrency. Reports F1
overall and per language, plus items/s and prefill/decode tok/s.

Per-language F1 is reported as undefined, not 0.0, when a slice contains no
positives.

## Task 2 — Comprehension (`bench_comprehension.py`)

Belebele, first 100 questions per language, 2 000 total. Passage + question +
4 options, single letter answer. Chance level 0.25.

Always the first N, never sampled, so every model sees identical questions.

## Task 3 — Translation (`bench_translate.py`)

FLORES-200 devtest, English → 19 languages, first 50 sentences each, 950
translations. chrF++ against the human reference.

Two mechanical checks alongside: English function words remaining in output,
and digit counts lost between source and output. Both are weak signals for
locating candidates to read, not scores. Digit group separators are stripped
before comparison.

## Task 4 — Coding (`bench_coding.py`)

HumanEval+ (163) and MBPP+ (378), 541 problems. Answer extracted from the code
block, concatenated with the problem's test suite, executed.

HumanEval/32 is excluded: its own canonical solution fails its own tests.
Validation run: 163/164 canonical solutions pass through this harness.

Execution drops to uid 65534 via `setpriv` when running as root, in a temp dir,
30 s timeout. Interpreter has numpy, scipy, sympy — several EvalPlus tests
import them.

## Task 5 — Latency (`bench.py`)

One request at a time, at three prompt sizes: about 500, 9 000 and 29 000
tokens. The prompt is Python source repeated to length followed by a request to
rewrite one function.

Reports time to first token, prefill rate and decode rate for each size. No
evaluation set is involved; the prompt is generated.

The longest prompt is 29 000 rather than 32 000 tokens because prompt and answer
share the [context window](glossary.md#context-window). At 32 768 configured, a
33 000-token prompt plus a 256-token answer does not fit, and every model
refuses it with HTTP 400.

## Task 6 — Long-form throughput (`bench_longform.py`)

Whole Wikipedia articles, 2 165 to 5 227 characters, 60 per run, six languages.
The model is asked for a one-word subject label. Long input, short output.

**Nothing is marked.** The answers are not checked against anything; the
measurement is articles per second and tokens per second at 1, 8, 32 and 64
requests in flight.

It exists because prompt length changes how an engine behaves, and every other
task here sends a sentence or a short passage. `harness/fetch_wikipedia.py`
collects the articles; the text is CC BY-SA 4.0 and each row keeps its page id,
revision id and URL.

## Loading

Every model is loaded twice in a row: once with the file not in memory, once
immediately afterwards with it still in the operating system's page cache. The
host's cache is dropped before the run so the first load is genuinely cold.

## Run rules

- Warm-up pass discarded (first pass after engine start runs ~40% slow during
  kernel autotune). Exception: coding, where every problem is distinct.
- `chat_template_kwargs: {enable_thinking: false}` sent; retried without it on
  400/422. `<think>` blocks stripped before marking.
- temperature 0.
- One model resident at a time.
- Failures recorded in the result JSON, not suppressed.

## Orchestration

`harness/run_all.py` loads each model through AI-Lab, waits for `/v1/models`,
loads it a second time to measure the warm case, runs the four quality tasks,
the short-prompt concurrency sweep, the latency test and the long-form sweep,
then unloads. `summary.json` is written after each model, so a run killed
halfway leaves usable results.

A model that fails to load is recorded and the run continues.

`harness/make_report.py` generates [quality.md](quality.md) from `results/`.
