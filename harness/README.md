# The harness

Each script *is* the definition of its test. [the method](../docs/method.md) explains the
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

## Where AI-Lab is

The scripts that talk to an AI-Lab manager take its address from `--manager`
(`--base-url` for OCR), otherwise from the environment variable
`AI_LAB_MANAGER`, otherwise from AI-Lab's own configuration file, named by the
environment variable `AI_LAB_CONFIG`: its `benchmark.manager_url`, or the
loopback address with its `port`. The address is not written into result files.

Everything else a script needs from the machine is in that file's `benchmark`
section, and a script that needs a value it does not find stops and names it:

| Setting | Used by |
|---|---|
| `benchmark.manager_url` | every script that calls the manager (optional, see above) |
| `benchmark.fish_tts_url` | `tts/runners/run_fish.py`, `tts/runners/run_libritts.py --engine fish`: Fish Speech's own `/v1/tts` |
| `benchmark.scratch_dir` | `measure_oversize.py`: where the hand-started llama.cpp writes its log |
| `benchmark.oversize_port` | `measure_oversize.py`: the port the hand-started llama.cpp listens on |

`shared/lab.py` reads them; `shared/textmetrics.py` and `shared/runs.py` hold what the transcription
scorers and the local generation runners share.

## The tests

| Script | What it measures |
|---|---|
| `bench_classify.py` | Topic classification, SIB-200, twenty languages. Quality **and** throughput from one pass |
| `bench_comprehension.py` | Reading comprehension, Belebele. Four options, one right, marked by letter |
| `bench_translate.py` | Translation, FLORES-200, chrF++ against human translations. Needs `sacrebleu` |
| `bench_coding.py` | 541 Python problems, HumanEval+ and MBPP+, marked by running the code |
| `bench_agentic.py` | Four architect-directed repository tasks with tool loops, protected files and hidden tests |
| `bench.py` | Single-stream latency at three prompt sizes. No corpus: it builds its own prompts |

Romanian speech has its own small harness under `audio/`:

| Script | Purpose |
|---|---|
| `audio/prepare_fleurs.py` | Selects FLEURS `ro_ro` test rows deterministically and creates mono 16 kHz WAV files |
| `audio/run_asr.py` | Loads every ASR model through AI-Lab and records WER, CER, timing and failures |
| `audio/run_vad.py` | Measures Silero VAD stability and speed; FLEURS has no boundary labels, so it does not invent a quality score |
| `audio/make_report.py` | Generates the public audio results page from raw JSON |

Every one of them reports correctness and speed from the same run.

## Helpers

| Script | Purpose |
|---|---|
| `evalcommon.py` | What all four share: talking to the engine, concurrency, timing, the result shape |
| `make_report.py` | Turns `results/` into `02-results.md`. The tables are generated, never typed |
| `textreport/` | The pages `make_report.py` writes: the tables in code, the fixed text in `textreport/prose/`, one Markdown file per page |
| `images/make_report.py` | Writes `../docs/images-ocr.md`: the results tables into the fixed text of `images/report-template.md` |
| `measure_oversize.py` | What a model larger than the card costs. The only script that does not go through AI-Lab |
| `run_vllm.sh`, `run_gguf.sh` | Start an engine by hand |
| `timeload.sh` | Time load and unload for either engine |
| `tokratio.py` | How many tokens the same text costs in different writing systems |

The vLLM 0.27.1 workaround for Gemma-4 (fix_gemma4.py and patch_gemma_cfg.py) edits one
machine's installed vLLM and model folders, so both scripts are kept with that machine's
private settings, not here — see [the bug](../docs/vllm-gemma4-bug.md).

## Safety

`bench_coding.py` and `bench_agentic.py` run code written by a language model. They run it as `nobody`,
in a throwaway directory, with a timeout — but it is still someone else's code
executing on your machine. **Run it in a container, not on your laptop.**

## Validating the harness itself

The coding test checks itself: all 164 HumanEval+ reference answers are run
through the same path, and 163 pass. The one failure is a problem whose own
reference answer fails its own tests, and it is excluded in the code with the
reason written down. An eval whose tests are wrong is worse than no eval.
