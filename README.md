# Gem12+ PRO + RTX PRO 4500 Blackwell - OCuLink — benchmark

The scope was to find out what the configuration can do, not to rank models in general.

**The word benchmark oversells this.** A benchmark in the proper sense repeats
every measurement, averages it, says how much it moved between runs, and follows
a published method so that its figures can be set beside somebody else's. None
of that happened here. Every number comes from one pass on one machine, taken to
work out roughly how much this configuration can carry so that jobs could be
sized around it. Read the figures as orders of magnitude that happen to have
decimal places on them, and where two of them sit close together, treat them as
the same number.

The tests were chosen from the work this machine actually does on personal
projects: multilingual text — sorting it, translating it, processing big volumes
of it, answering questions about it — writing code, and Romanian speech.

## Pages

| | |
|---|---|
| [Configuration](docs/machine.md) | Hardware, engines, and how the GPU is attached |
| [Models](docs/models.md) | What was tested, how large, and why these ten |
| [Method](docs/method.md) | How each task was run, and where the data comes from |
| [Quality](docs/quality.md) | Classification, comprehension, translation, coding |
| [Throughput](docs/throughput.md) | How much work per second, short and long prompts |
| [Latency](docs/latency.md) | One request at a time, at 500 / 9 k / 29 k tokens |
| [Loading](docs/loading.md) | Cold and warm load times; a model larger than VRAM |
| [vLLM start sequence](docs/vllm-startup.md) | Where the minutes go, and the flag that removes 72 seconds |
| [Partial offload](docs/partial-offload.md) | What it costs to run a model that does not fit |
| [Tokenizer cost](docs/tokenizer.md) | What the same text costs in each language |
| [Findings](docs/findings.md) | What follows from all of it |
| [Glossary](docs/glossary.md) | Every term used in a table |
| [Romanian audio method](docs/audio-method.md) | Corpus, selection, normalisation and scoring for speech models |
| [Audio models](docs/audio-models.md) | ASR and VAD models, revisions, licences and exclusions |
| [Romanian audio results](docs/audio-results.md) | Accuracy, processing speed, loading and every recorded failure |
| [Audio findings](docs/audio-findings.md) | What the Romanian pass suggests for real workloads |

Also kept: [an earlier four-engine study](docs/engines-2026-08.md),
and [dead ends](docs/dead-ends/README.md) — measurement errors and a conclusion that
measuring overturned.

Start with [Findings](docs/findings.md) if you want the conclusions, or
[Quality](docs/quality.md) if you want the numbers.

## Datasets

Five of these are evaluation sets. Four contain text with the correct answer
recorded next to it; FLEURS contains speech with a reference transcript. The
model sees the input without its reference, and its reply is compared with the
recorded one.

The Wikipedia articles have no answers. They are long text, used for measuring
speed.

| Set | What it gives | Why this one |
|---|---|---|
| FLORES-200 | the same 1 012 sentences translated into 200 languages | translation can be compared against a human reference instead of against another model |
| SIB-200 | a topic label on those same sentences | turns them into a classification task with a right answer |
| Belebele | a question and four answers on those same passages | comprehension, scored by reading one letter |
| HumanEval+ / MBPP+ | Python problems with tests | the code is executed; it passes or it does not |
| Wikipedia | whole articles, 2 165 to 5 227 characters, six languages | a real long prompt rather than a sentence |
| FLEURS `ro_ro` | Romanian read speech with human transcriptions | one official test split can measure both ASR accuracy and processing speed |
| Echo Synthetic Diarization | Romanian synthetic meetings with RTTM speaker turns | compares diarization on 2–5 speakers, with and without overlap |

Three of them are built on FLORES, so the same sentences are being sorted,
understood and translated. A weakness in one language shows up in all three at
once rather than being hidden by three different corpora.

Sources and licences are in [the text method](docs/method.md) and
[audio method](docs/audio-method.md). Nothing is redistributed here: the sets
are fetched from their publishers and a manifest records what came from where.

## Running it

```sh
python3 harness/get_datasets.py --out ./eval-data     # ~57 MB, from the publishers
python3 harness/fetch_wikipedia.py --out ./eval-data/wikipedia_articles.jsonl
python3 harness/run_all.py --out ./results
python3 harness/make_report.py --results ./results --out ./docs
```

Romanian audio is prepared and run separately on Data-Lab, which owns the
downloaded corpus and calls AI-Lab over the private network:

```sh
python3 harness/audio/prepare_fleurs.py 0000.parquet --out ./fleurs-ro --limit 100
python3 harness/audio/run_asr.py --data ./fleurs-ro --out ./results/audio/asr
python3 harness/audio/run_vad.py --data ./fleurs-ro --out ./results/audio/vad.json
hf download --repo-type dataset upb-nlp/echo-synthetic-diarization \
  --revision b627c5bf437937d90efafc7cf76d5dcfb3195f35 \
  --local-dir ./echo-synthetic-diarization
python3 harness/audio/run_diarization.py --data ./echo-synthetic-diarization --out ./results/audio/diarization
python3 harness/audio/make_report.py --results ./results/audio --out ./docs/audio-results.md
```

`harness/bench_coding.py` executes code written by a language model. It drops to
`nobody` in a temporary directory with a timeout, but run it in a container.

## Caveats

Seven things to know before drawing conclusions from any table here.

### Every number is from a single run

Each test was run once per model. Nothing was repeated and averaged, so there
is no way to say how much a figure would move if it were run again.

Models are not perfectly repeatable even with randomness switched off, and the
configuration is not in an identical state twice. The scope here was to give a
rough idea of the limits and of what to expect.

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

### The audio studies are controlled baselines, not the target domain

The Romanian audio pass uses 100 rows selected at equal intervals across the
official FLEURS test parquet. This keeps the seven-model run manageable and
makes the selection exactly reproducible, but it is too small to establish a
general Romanian ASR ranking or performance on political meetings, telephone
audio and noisy local reporting.

**What to do with that:** use it to choose candidates for the next, domain-
specific evaluation. Differences that are small need a larger corpus and
repeated runs.

The diarization pass uses all 120 files in Echo Synthetic Diarization. They are
Romanian and have exact RTTM speaker references, but they are synthetic
mixtures rather than recordings from council chambers, public debates or local
video streams. Use the result to compare candidates, then validate the winner
on manually labelled material from the intended production domain.

## Licence

MIT for the harness, the documents and the results. The evaluation sets are not
ours and are not here; each keeps its own licence, recorded in
`eval-data/MANIFEST.json` once fetched.
