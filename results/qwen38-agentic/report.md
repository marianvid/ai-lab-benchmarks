# Qwen3.8-27B on AOOSTAR Linux

Date: 2026-09-15

## Verdict

Keep **Qwen3.8-27B Q6_K** if Qwen3.8 is wanted for further agent experiments. Do not promote
**Q8_0** to the core set: in these runs it used 4.5 GiB more VRAM and 5.26 GB more storage,
without improving either the architect-directed agent suite or HumanEval+/MBPP+.

Neither Qwen3.8 quant replaces the current high-throughput Linux coding models. The dense 27B
model is materially slower, while its standard coding score is only level with Qwen3.6 NVFP4
and slightly below Qwopus3.6. Q6_K is therefore a useful benchmark/secondary agent model, not
the default volume endpoint.

## Models and runtime

Both GGUF files are from `bartowski/Qwen3.8-27B-GGUF`, pinned at repository commit
`125a02af4987b57c7deb88d7f2ec58a5725c07c0`.

| Quant | File bytes | Runtime VRAM, agent profile | Runtime VRAM, 8-slot profile |
|---|---:|---:|---:|
| Q6_K | 23,860,565,728 | 22,786 MiB | 24,514-24,638 MiB |
| Q8_0 | 29,116,388,960 | 27,302 MiB | 29,030 MiB |

Both fit completely in the RTX 5090 VRAM. No RAM offload was used. The engine was updated from
llama.cpp b10448 (`0d9ceae1e`) to v0.4.1 / build b10964 (`b29c606e2`) for current Qwen3.8 support.

## Architect-directed coding agent suite

Profile: 32K context, one slot, reasoning `xhigh`, tool calling enabled. Four small repositories
test exact Decimal rules, a multi-file domain/service/repository boundary, an idempotent config
migration, and resistance to a prompt injection embedded in a fixture. Visible and hidden unit
tests are executed after the model finishes.

| Model | Passed | Wall | Prompt tokens | Completion tokens | Tool turns |
|---|---:|---:|---:|---:|---:|
| Qwen3.8-27B Q6_K | 3/4 | 319.379 s | 34,081 | 9,693 | 20 |
| Qwen3.8-27B Q8_0 | 3/4 | 394.592 s | 39,695 | 10,371 | 21 |
| Qwopus3.6-27B-Coder Q5_K_M (control) | 3/4 | 134.460 s | 25,035 | 4,538 | 21 |

All three models failed the same hidden assertion in `config-migration`: they removed obsolete
auto-generated profiles and preserved user data correctly, but returned `{version: 2}` instead
of `{version: 2, profiles: {}}` when the input had no `profiles` key. Protected architect,
test, and fixture files remained unchanged in every run. Q6 was 19.1% faster than Q8; Qwopus
was 2.38x faster than Q6 with the same pass count.

This is a single pass at temperature 1.0, so it is a behavioral probe rather than a statistically
stable ranking. The shared failure also means this four-case suite does not distinguish the three
models on total score; its timing and failure details remain useful.

## Standard coding suite

Method matches the existing Linux report: 541 HumanEval+ and MBPP+ problems, concurrency 8,
thinking disabled, generated programs run as `nobody`, and the benchmark virtual environment is
used for test dependencies.

| Model | Format | Passed | Pass rate | Wall | Decode tok/s |
|---|---|---:|---:|---:|---:|
| Gemma-4-26B-A4B | GGUF | 451/541 | 83.36% | 688.64 s | 125.1 |
| Qwopus3.6-27B-Coder | NVFP4 | 441/541 | 81.52% | 304.90 s | 233.3 |
| Qwen3.8-27B Q6_K | GGUF | 438/541 | 80.96% | 894.72 s | 87.8 |
| Qwen3.6-35B-A3B | NVFP4 | 438/541 | 80.96% | 147.69 s | 480.5 |
| Qwen3.6-35B-A3B | GGUF | 437/541 | 80.78% | 486.95 s | 134.7 |
| Qwen3.8-27B Q8_0 | GGUF | 436/541 | 80.59% | 839.01 s | 91.6 |

Q8 generated 1,758 fewer tokens than Q6, explaining why this particular pass finished faster
despite the larger quant. The two-answer score gap is too small to treat as a robust quality
difference, but it clearly provides no evidence that Q8 improves quality enough to justify its
resource cost.

An initial Q6 standard pass was discarded because generated programs were accidentally executed
with the system Python and all failed on a missing `numpy`. It was repeated from scratch with
`BENCH_PYTHON=/opt/bench/.venv/bin/python`; only the corrected 438/541 run is archived here.

## Recommendation

- Keep Q6_K in benchmark storage for further agentic workflow experiments.
- Q8_0 is a deletion candidate after the user decides that no repeat/statistical run is needed.
- Keep Qwopus/Qwen3.6 vLLM for volume: they deliver comparable quality much faster.
- Do not infer that Qwen3.8 is generally weaker from this local test alone; this verdict is about
  these quantizations, this hardware, and these workloads.

Model references:

- Official model card: https://huggingface.co/Qwen/Qwen3.8-27B
- GGUF quant repository: https://huggingface.co/bartowski/Qwen3.8-27B-GGUF
