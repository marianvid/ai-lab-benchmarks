# The harness

Each script *is* the definition of its test. `../01-method.md` explains the
intent behind them; this file says what to run.

## Getting the data

```sh
python3 get_datasets.py --out ./eval-data
```

Downloads FLORES-200, SIB-200, Belebele and HumanEval+/MBPP+ from the people who
published them, for twenty languages, and writes `MANIFEST.json` with the
licences. **Nothing is redistributed by this repository.**

## Running everything

```sh
python3 run_all.py --out ./results
```

One model at a time: load it through [AI-Lab](https://github.com/marianvid/ai-lab), wait until it answers, run the four
tests, unload, record what loading and unloading cost. It is built to survive
its own failures — a model that will not start is a recorded fact, not a stop.

## The tests

| Script | What it measures |
|---|---|
| `bench_classify.py` | Topic classification, SIB-200, twenty languages. Quality **and** throughput from one pass |
| `bench_comprehension.py` | Reading comprehension, Belebele. Four options, one right, marked by letter |
| `bench_translate.py` | Translation, FLORES-200, chrF++ against human translations. Needs `sacrebleu` |
| `bench_coding.py` | 541 Python problems, HumanEval+ and MBPP+, marked by running the code |
| `bench.py` | Single-stream latency at three prompt sizes. No corpus: it builds its own prompts |

Every one of them reports correctness and speed from the same run.

## Helpers

| Script | Purpose |
|---|---|
| `evalcommon.py` | What all four share: talking to the engine, concurrency, timing, the result shape |
| `make_report.py` | Turns `results/` into `02-results.md`. The tables are generated, never typed |
| `measure_oversize.py` | What a model larger than the card costs. The only script that does not go through AI-Lab |
| `run_vllm.sh`, `run_gguf.sh` | Start an engine by hand |
| `timeload.sh` | Time load and unload for either engine |
| `tokratio.py` | How many tokens the same text costs in different writing systems |
| `fix_gemma4.py`, `patch_gemma_cfg.py` | The vLLM patch — see `../05-a-bug-in-vllm.md` |

## Safety

`bench_coding.py` runs code written by a language model. It runs it as `nobody`,
in a throwaway directory, with a timeout — but it is still someone else's code
executing on your machine. **Run it in a container, not on your laptop.**

## Validating the harness itself

The coding test checks itself: all 164 HumanEval+ reference answers are run
through the same path, and 163 pass. The one failure is a problem whose own
reference answer fails its own tests, and it is excluded in the code with the
reason written down. An eval whose tests are wrong is worse than no eval.
