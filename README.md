# RTX PRO 4500 Blackwell — inference benchmark

llama.cpp and vLLM on a single 32 GB card, eGPU over OCuLink. Eight
model/engine combinations, four tasks, 20 languages.

Measured 19–20 August 2026. Raw JSON in `results/`; `02-results.md` is
generated from it.

## Hardware

| | |
|---|---|
| GPU | NVIDIA RTX PRO 4500 Blackwell, 32 GB (32 623 MiB), 200 W cap, ECC on |
| Attachment | OCuLink eGPU dock, PCIe address 01:00.0 |
| Driver | 610.57.04, CUDA 13 |
| Host | AOOSTAR GEM12+ Pro, Ryzen 7 PRO 8845HS (8C/16T), 96 GB DDR5-5600, 35 W BIOS cap |
| OS | Proxmox; engines in an unprivileged LXC |
| Engines | llama.cpp b10447, vLLM 0.26.1rc1.dev949 |
| Model storage | internal NVMe |

## Tasks

| Task | Set | Items | Metric |
|---|---|---:|---|
| Classification | SIB-200, 20 languages | 4 080 | F1, binary (`politics` vs rest, 15% positive) |
| Comprehension | Belebele, 20 languages | 2 000 | accuracy, 4-way MCQ (chance 0.25) |
| Translation | FLORES-200, en→19 | 950 | chrF++ vs human reference |
| Coding | HumanEval+ / MBPP+ | 541 | pass rate, tests executed |

All sets public (CC BY-SA 4.0 / Apache 2.0), none redistributed here.
`harness/get_datasets.py` fetches them.

Every task records throughput and wall time alongside the score.

## Results

Full tables in `02-results.md`. Summary:

| Model | Engine | Cls F1 | Comp | chrF++ | Code | Cls items/s | Load |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwopus3.6-27B-Coder | vLLM | **0.906** | **0.915** | 52.99 | 0.815 | 19.7 | 69.6 s |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 0.913 | 54.24 | 0.808 | 8.0 | 10.8 s |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 0.895 | 53.79 | 0.810 | 53.6 | 98.1 s |
| Gemma-4-26B-A4B | vLLM | 0.875 | 0.873 | 55.80 | 0.826 | **51.1** | 45.1 s |
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 0.884 | **56.12** | **0.834** | 8.9 | 9.3 s |
| Gemma-4-E4B (4.6 GB) | llama.cpp | 0.828 | 0.760 | 54.08 | 0.765 | 11.6 | **3.3 s** |
| GLM-4.7-Flash | vLLM | 0.819 | 0.742 | 50.39 | 0.706 | 37.0 | 98.3 s |
| Qwen3-Coder-30B-A3B | vLLM | 0.726 | 0.847 | 45.38 | 0.791 | 49.9 | 45.1 s |

Unload is 2.0–2.6 s for every combination.

### Throughput vs concurrency

Classification, 3 languages, concurrency 1 → 64:

| Model | Engine | c=1 | c=8 | c=32 | c=64 | gain |
|---|---|---:|---:|---:|---:|---:|
| Gemma-4-26B-A4B | vLLM | 8.7 | 54.4 | 164.7 | 169.7 | 19.6× |
| GLM-4.7-Flash | vLLM | 10.6 | 56.6 | 149.2 | 165.7 | 15.7× |
| Qwen3-Coder-30B-A3B | vLLM | 12.0 | 62.0 | 175.6 | 176.6 | 14.7× |
| Qwopus3.6-27B-Coder | vLLM | 3.2 | 19.4 | 43.8 | 43.9 | 13.5× |
| Qwen3.6-35B-A3B | vLLM | 14.8 | 60.0 | 105.3 | 105.7 | 7.1× |
| Gemma-4-E4B | llama.cpp | 11.7 | 12.4 | 12.4 | 12.4 | 1.1× |
| Gemma-4-26B-A4B | llama.cpp | 9.4 | 9.5 | 9.6 | 9.8 | 1.0× |
| Qwen3.6-35B-A3B | llama.cpp | 8.0 | 8.1 | 8.4 | 8.1 | 1.0× |

### Tokenizer cost by language

Same FLORES sentences, Gemma-4-26B tokenizer, tokens relative to English:

`lt 1.66 · th 1.65 · uk 1.64 · ro 1.57 · pl 1.52 · ta 1.49 · ar 1.48 ·
fr 1.41 · ru 1.40 · ko 1.39 · vi 1.37 · tr 1.36 · de 1.34 · hi 1.31 ·
es 1.29 · pt 1.26 · ja 1.24 · bn 1.23 · zh 1.12 · en 1.00`

Script is not the predictor: Han is cheapest after English, Latin-script
Lithuanian is most expensive. An 8 192-token window holds ~60% as much
Lithuanian as English.

### Model larger than VRAM

`Qwen3-Coder-Next-UD-Q4_K_XL`, 46.2 GB, on a 32 GB card:

| | |
|---|---|
| Load | 10.5 s (warm page cache) |
| VRAM | 30 728 MB |
| Generation | 56.4 tok/s (llama.cpp timing), 42.0 tok/s wall-clock |

Requires letting llama.cpp pick the split. With `--n-gpu-layers 36` it aborts:
`common_fit_params: failed to fit params to free device memory: n_gpu_layers
already set by user to 36, abort`, then `cudaMalloc failed` on 34 406 MiB.

AI-Lab refuses this configuration by design — partial offload over OCuLink puts
every token across the cable. Measured outside AI-Lab.

## Reproducing

```sh
python3 harness/get_datasets.py --out ./eval-data     # ~57 MB, 20 languages
python3 harness/run_all.py --out ./results            # one model at a time
python3 harness/make_report.py --results ./results --out 02-results.md
```

`bench_coding.py` executes model-generated Python. It drops to `nobody` in a
temp dir with a timeout, but run it in a container.

## Caveats

- Single run per cell. No error bars. Treat F1 deltas under 0.02 as noise.
- Sentence- and passage-level inputs. Long-context behaviour is not covered
  here; see `bench.py` for a separate latency test at 300 / 8 k / 32 k tokens.
- HumanEval+ and MBPP+ are in every model's training data. Irrelevant for
  measuring machine throughput; do not read the pass rates as reasoning scores.
- HumanEval/32 excluded: its own reference solution fails its own tests
  (163/164 references pass through this harness).
- Single-turn only. No agent-loop or long-conversation behaviour.

## Files

| | |
|---|---|
| `01-method.md` | Task definitions, metrics, run rules |
| `02-results.md` | Generated tables |
| `03-engines.md` | TensorRT-LLM and SGLang comparison (August 2026, different corpus) |
| `04-what-it-means.md` | Findings and selection guidance |
| `05-a-bug-in-vllm.md` | Gemma-4 load failure in vLLM 0.27.1: cause and patch |
| `dead-ends/` | Measurement errors and a conclusion that measuring overturned |
| `harness/` | Scripts |
| `results/` | Raw JSON, 68 files |

MIT for the harness, documents and results. Evaluation sets keep their own
licences; see `eval-data/MANIFEST.json` after fetching.
