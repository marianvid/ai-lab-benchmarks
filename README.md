# Gem12+ PRO + RTX PRO 4500 Blackwell - OCuLink — benchmark

The scope was to find out what the configuration can do, not to rank models in general.

## Pages

| | |
|---|---|
| [Configuration](docs/machine.md) | Hardware, engines, and how the GPU is attached |
| [Models](docs/models.md) | What was tested, how large, and why these eight |
| [Method](docs/method.md) | How each task was run, and where the data comes from |
| [Quality](docs/quality.md) | Classification, comprehension, translation, coding |
| [Throughput](docs/throughput.md) | How much work per second, short and long prompts |
| [Latency](docs/latency.md) | One request at a time, at 500 / 9 k / 29 k tokens |
| [Loading](docs/loading.md) | Cold and warm load times; a model larger than VRAM |
| [Tokenizer cost](docs/tokenizer.md) | What the same text costs in each language |
| [Findings](docs/findings.md) | What follows from all of it |
| [Glossary](docs/glossary.md) | Every term used in a table |

Also kept: [an earlier four-engine study](docs/engines-2026-08.md) from August,
and [dead ends](docs/dead-ends/) — measurement errors and a conclusion that
measuring overturned.

Start with [Findings](docs/findings.md) if you want the conclusions, or
[Quality](docs/quality.md) if you want the numbers.

## The short version

| Model | Engine | Classification F1 | Sentences/s |
|---|---|---:|---:|
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

vLLM adds requests to a batch already running; llama.cpp does not.
The real advantage of vLLM lies in concurrency.

**Prompt length changes that.** Measured again with whole articles instead of
sentences, one model's batching advantage went from 13.5× to 1.6×, and
another's from 15.7× to 8.3×. A long prompt occupies far more cache, so fewer
requests fit at once.

**Load times depend on the page cache more than on the model.** A cold vLLM
start took 212 seconds where the warm one took 117.

## Reproducing

```sh
python3 harness/get_datasets.py --out ./eval-data     # ~57 MB, from the publishers
python3 harness/fetch_wikipedia.py --out ./eval-data/wikipedia_articles.jsonl
python3 harness/run_all.py --out ./results
python3 harness/make_report.py --results ./results --out ./docs
```

No evaluation data is stored in this repository. The first two commands fetch it
from FLORES-200, SIB-200, Belebele, EvalPlus and Wikipedia, all under CC BY-SA
4.0 or Apache 2.0, and write a manifest recording what came from where.

`harness/bench_coding.py` executes code written by a language model. It drops to
`nobody` in a temporary directory with a timeout, but run it in a container.

## Caveats

Six things to know before drawing conclusions from any table here.

### Every number is from a single run

Each test was run once per model. Nothing was repeated and averaged, so there
is no way to say how much a figure would move if it were run again.

It would move somewhat. Models are not perfectly repeatable even with
randomness switched off, and the configuration is not in an identical state
twice.

**What to do with that:** on the classification score, a difference smaller
than about 0.02 should be read as "the same". There are roughly 600 positive
examples in that set, so a handful of sentences judged differently moves the
score by that much on its own. Two models at 0.889 and 0.895 have not been
separated by this benchmark.

### Every measurement is one question and one answer

The model is asked something, it replies, the exchange ends. Nothing here sends
a follow-up.

That leaves out how a model behaves inside an agent that goes back and forth
twenty times over the same code, or in a conversation whose history keeps
growing. Both work the engine differently: the same text is re-sent repeatedly,
and an engine can reuse the part of a prompt it has already processed.

**What to do with that:** the throughput figures describe batch work — many
independent requests. They do not describe an agent session.

### The coding problems are in every model's training data

HumanEval and MBPP have been public for years. Every model measured here has
almost certainly seen them during training, so a good score partly reflects
memory rather than reasoning.

That would ruin a study asking which model is the better programmer. It does
not affect this one, which asks how fast this configuration gets through a
fixed amount of Python. The problems are identical for every model, they
execute, and they pass or fail mechanically — that is all this needs from them.

**What to do with that:** read the coding column as throughput and correctness
on a known workload, not as evidence of reasoning ability.

### The tests did not all run with the same context window

The context window is the largest number of tokens one request may contain,
prompt and answer together. It is set per model instance, and a larger window
reserves more VRAM, which leaves less room for handling several requests at
once.

The four quality tasks ran at 8 192 tokens. The latency test and the long-form
throughput ladder need longer prompts than that, so they ran at 32 768.

**What to do with that:** do not place a throughput figure from the quality
section beside one from the long-form section and treat them as the same
measurement. Each page states which setting applied.

### Load times are given twice, cold and warm

When a file has been read recently the operating system keeps a copy of it in
RAM — the page cache — and reading it again skips the disk entirely. The second
load of a model is therefore much faster than the first, and a load time quoted
without saying which one it was is close to meaningless.

The host's page cache was emptied before the run, so the **cold** column is a
genuine first read. The **warm** column is a second load taken immediately
afterwards.

**What to do with that:** if models sit on disk between uses, the cold column
is the one that applies. If a model is reloaded repeatedly, the warm one is.

### The translation scores look low, and the languages are why

chrF++ compares a translation with a reference by counting shared character
sequences. How high anyone scores depends heavily on which languages are being
translated into. These 19 include Tamil, Thai, Bengali and Lithuanian, all of
which every model handles worse than French or Spanish.

A study covering only western European languages would report numbers ten to
fifteen points higher for these same models, and it would not mean they were
better.

**What to do with that:** compare the models with each other inside that table.
Do not compare the numbers against a chrF++ figure published anywhere else.

## Licence

MIT for the harness, the documents and the results. The evaluation sets are not
ours and are not here; each keeps its own licence, recorded in
`eval-data/MANIFEST.json` once fetched.
