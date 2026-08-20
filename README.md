# RTX PRO 4500 Blackwell — inference benchmark

llama.cpp against vLLM on a single 32 GB card, attached as an external GPU over
OCuLink. Eight model and engine combinations, four tasks, 20 languages.

Measured 19–20 August 2026 on one machine. The point was to find out what that
machine can do, not to rank models in general.

## Pages

| | |
|---|---|
| [The machine](docs/machine.md) | Hardware, engines, and how the GPU is attached |
| [The models](docs/models.md) | What was tested, how large, and why these eight |
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

**The engine decides throughput; the model decides quality.** The same weights
on both engines:

| Model | Engine | Classification F1 | Sentences/s |
|---|---|---:|---:|
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

Same answers, six and a half times the work. vLLM adds requests to a batch
already running; llama.cpp does not. At one request at a time the two are level,
and llama.cpp starts in seconds where vLLM takes minutes.

**Prompt length changes that.** Measured again with whole articles instead of
sentences, one model's batching advantage went from 13.5× to 1.6×, and
another's from 15.7× to 8.3×. A long prompt occupies far more cache, so fewer
requests fit at once. Benchmarking on sentences and deploying on documents does
not give you the throughput you measured.

**Load times depend on the page cache more than on the model.** A cold vLLM
start took 212 seconds where the warm one took 117 — most of the difference is
vLLM's own multi-gigabyte installation being read from disk, not the model.

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

- **One run per cell.** No error bars. Treat differences under 0.02 F1 as noise.
- **Single-turn only.** Nothing here measures an agent loop or a long
  conversation.
- **The coding problems are in every model's training data.** They are old and
  public. That would invalidate a study ranking models by reasoning; here they
  are a fixed executable workload for measuring a machine.
- **Quality was measured at an 8 192-token context**, latency and the long-form
  throughput ladder at 32 768. Both are stated on the relevant pages.
- **Load times are reported cold and warm.** The host's page cache was dropped
  before the run so the cold figures are genuine.
- **The translation scores are low in absolute terms** because the language mix
  includes Tamil, Thai, Bengali and Lithuanian. Compare within the table only.

## Licence

MIT for the harness, the documents and the results. The evaluation sets are not
ours and are not here; each keeps its own licence, recorded in
`eval-data/MANIFEST.json` once fetched.
