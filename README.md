# Local inference benchmarks — one 32 GB card, twenty languages, two engines

**Why this exists.** Not to compare inference engines in the abstract. To find
out where the limits of one particular machine are — a single 32 GB GPU on a
mini PC — so that work could be planned against what it can actually do: what
fits, how long it takes, and at what size the trade-offs start.

Everything here was measured on that machine on 19–20 August 2026. The numbers
are not predictions, and they are not copied from anyone's product page. Every
one of them came from a script in `harness/`, and the raw output of every run is
in `results/`.

Eight model-and-engine combinations, four tests, twenty languages, one card.

## What stood out

| | |
|---|---|
| **Same weights, six times the work** | Qwen3.6-35B on llama.cpp: 8.0 sentences/s. The same model on vLLM: **53.6**. Quality identical to within 0.006 F1 |
| **7.1× to 19.6×** from batching alone | vLLM, as concurrency rises from 1 to 64. llama.cpp on the same hardware: **1.0× to 1.1×** — it does not get faster when you send it more |
| **A 46 GB model runs on a 32 GB card** | 56 tokens/second, with llama.cpp choosing the split itself. Told to force the split, it refuses to fit at all |
| **A 4.6 GB model scores 0.828** | Against 0.906 for the best in the set, and it loads in 3.3 seconds |
| **The coding model is last at language** | Fastest at reading prompts, and bottom of every language test: 0.726 F1 against 0.906, translation 45.4 against 56.1 |
| **llama.cpp starts in 3–11 seconds, vLLM in 45–98** | For one question and out, the slower engine wins on the only clock that matters |
| **A context window holds 40% less Lithuanian than English** | And Chinese, in Han characters, is the *cheapest* language measured. The tokenizer's familiarity decides the cost, not the alphabet |

## The machine

A home lab, not a server room. This matters: the results describe what a
single-GPU desktop-class machine does, and the bottlenecks are that machine's.

| | |
|---|---|
| Mini PC | AOOSTAR GEM12+ Pro — AMD Ryzen 7 PRO 8845HS, 8 cores / 16 threads |
| Memory | 96 GB DDR5-5600 |
| CPU power target | 35 W, set in the BIOS |
| GPU | **NVIDIA RTX PRO 4500 Blackwell, 32 GB, 200 W limit, ECC on** |
| How the GPU is attached | **External, over OCuLink** — an eGPU dock, not a card in a slot |
| Driver | 610.57.04, CUDA 13 |
| Operating system | Proxmox; the engines run inside an unprivileged Linux container |
| Model storage | NVMe |

**The OCuLink link is worth stating plainly.** The GPU is outside the machine,
connected through a cable, and that link is narrower than a motherboard slot.
It costs nothing once a model is loaded — the weights sit in VRAM and inference
never crosses the link — but it is why load times are reported separately from
inference speed throughout.

The same application also runs on an Apple M3 Max. **Nothing here was measured
on it.**

## How to read this

| | |
|---|---|
| `01-method.md` | The four tests, what each measures, and what the words mean |
| `02-results.md` | The numbers, by task |
| `03-engines.md` | Four engines compared — an earlier study, kept because its conclusion still holds |
| `04-what-it-means.md` | What follows from the numbers, and what to choose |
| `05-a-bug-in-vllm.md` | A bug found, diagnosed and patched during the study |
| `dead-ends/` | What was tried and did not work, and what was concluded and was wrong |

Read `04-what-it-means.md` if you only read one. The point of the study was to
be able to choose, and that document is the choosing.

## Reproducing it

**No evaluation data is redistributed here.** One script fetches all of it from
the people who published it:

```sh
python3 harness/get_datasets.py --out ./eval-data
python3 harness/run_all.py --out ./results
```

The sets are FLORES-200, SIB-200, Belebele and HumanEval+/MBPP+ — all public,
all CC BY-SA 4.0 or Apache 2.0, and all with human-made ground truth.
`eval-data/MANIFEST.json` records what was downloaded, from where, and under
what terms.

`results/` holds the JSON output of every run in this repository, and
`02-results.md` is generated from it rather than typed. Any number in that
document can be traced to the file it came from.

## Licence

The harness, the documents and the results: MIT, see `LICENSE`. The evaluation
sets are not ours and are not here; each keeps its own licence, recorded in
`eval-data/MANIFEST.json` once you fetch them.
