# macOS AI-Lab image benchmark

## Environment

- Platform: macOS 15.7.3 (24G407)
- Hardware: MacBook Pro Mac15,9, Apple M3 Max, 16 CPU cores, 128 GB unified memory
- Runtime: ComfyUI 0.34.0, Python 3.11.7, torch 2.13.0
- Device reported by ComfyUI during the final FLUX.2 Dev runs: Apple MPS with unified memory
- Public manager API: `http://127.0.0.1:8110` using the isolated macOS benchmark configuration
- Generation fixtures: 1024x1024 for the current large-model profiles; identical prompts, seeds and 20-step workflows for FLUX.2 Dev Q8_0 and BF16

## Executive result

The Mac is a valid execution target for every requested current workflow. FLUX.2 Klein 4B BF16, FLUX.2 Dev Q8_0, FLUX.2 Dev BF16, Qwen Image generation, Qwen Image Edit BF16 and both OCR profiles completed without OOMs. The only incompatible path is the older FLUX.2 FP8 workflow, whose float8 type is unsupported by this runtime; Q8_0 and BF16 are the supported FLUX.2 Dev alternatives.

- Current generation profiles: 20/20 successful fixtures
- Qwen Image Edit BF16: 3/3 successful fixtures
- OCR: 8/8 completed, 0 model failures, 0 infrastructure errors
- OOMs: 0
- Legacy FLUX.2 FP8: 0/5, runtime incompatible (`Undefined type Float8_e4m3fn`)
- Earlier SD 1.5 and Qwen Image baseline: 10/10 execution successes

## Comparative performance

| Workflow | Precision / format | Fixtures | Success | Mean latency | Median latency | Practical role |
|---|---|---:|---:|---:|---:|---|
| FLUX.2 Klein 4B | BF16 | 5 | 5/5 | 23.0 s | 17.6 s | Interactive local generation |
| FLUX.2 Dev 32B | Q8_0 GGUF | 5 | 5/5 | 17 min 27 s | 17 min 7 s | Preferred full Dev path on Mac |
| FLUX.2 Dev 32B | BF16 safetensors | 5 | 5/5 | 20 min 13 s | 20 min 32 s | Full-precision reference and quality comparison |
| Qwen Image | FP8 model stack accepted by runtime | 5 | 5/5 | 20 min 15 s | 20 min 20 s | Strong generation baseline, including typography |
| Qwen Image Edit | BF16 | 3 | 3/3 | 41 min 51 s | 42 min 3 s | High-latency local editing |

FLUX.2 Dev Q8_0 is approximately 13.7% faster than BF16 on the identical five-fixture suite. Klein 4B is approximately 52.7 times faster than Dev BF16 by mean latency, so it is the clear interactive option. Dev BF16 and Qwen Image generation have effectively equal mean latency on this machine. Qwen Image Edit is usable but should be scheduled as a long-running job.

## Per-fixture generation latency

| Profile | Composition | Typography | Spatial | Character sheet | Romanian scene |
|---|---:|---:|---:|---:|---:|
| FLUX.2 Klein 4B BF16 | 44.7 s | 17.9 s | 17.5 s | 17.5 s | 17.6 s |
| FLUX.2 Dev Q8_0 | 18 min 25 s | 18 min 13 s | 16 min 40 s | 16 min 53 s | 17 min 7 s |
| FLUX.2 Dev BF16 | 21 min 29 s | 20 min 49 s | 18 min 49 s | 19 min 28 s | 20 min 32 s |
| Qwen Image | 19 min 39 s | 20 min 34 s | 20 min 15 s | 20 min 20 s | 20 min 25 s |

## OCR

| Profile | Executed | Exact matches | Mean CER | Mean confidence |
|---|---:|---:|---:|---:|
| `ocr-smoke` | 4/4 | 2 | 0.021905 | 0.977705 |
| `ocr-server` | 4/4 | 3 | 0.025000 | 0.981510 |

Both OCR paths are operational on macOS. Across all eight fixtures there were no model or infrastructure failures.

## Interpretation

1. Use FLUX.2 Klein 4B BF16 for interactive work and rapid iteration.
2. Use FLUX.2 Dev Q8_0 as the default full-size Dev workflow on Mac; it preserves the complete 32B path while reducing mean latency relative to BF16.
3. Keep FLUX.2 Dev BF16 as the reference workflow when quantization differences matter. It is compatible and stable, but each 1024x1024 generation takes roughly 19-21 minutes.
4. Use Qwen Image when its typography and prompt-following behavior are preferred; its latency is effectively the same as Dev BF16.
5. Queue Qwen Image Edit BF16 as a background task because each edit takes roughly 42 minutes.
6. Do not schedule the legacy FLUX.2 FP8 workflow on this runtime. This is a dtype compatibility issue, not an OOM or evidence that FLUX.2 Dev is unsupported on macOS.

## Semantic review

All 28 generated artifacts now have manual rubric review. Execution success and semantic success remain separate measurements.

| Profile | Cases passed | Criteria passed | Result |
|---|---:|---:|---|
| SD 1.5 | 0/5 | 10/24 | Execution works, but prompt adherence is weak. |
| Qwen Image | 5/5 | 24/24 | Full generation rubric pass. |
| FLUX.2 Klein 4B BF16 | 4/5 | 22/24 | Strong overall; the character sheet lacks explicit panels and one requested pose. |
| FLUX.2 Dev Q8_0 | 5/5 | 24/24 | Full generation rubric pass. |
| FLUX.2 Dev BF16 | 5/5 | 24/24 | Full generation rubric pass. |
| Qwen Image Edit BF16 | 2/3 | 11/12 | Color and background edits pass; label edit also alters the mug slightly. |

Q8_0 and BF16 are semantically tied on this five-case pass, so the 13.7% Q8_0 latency advantage makes it the practical default. This single pass is not evidence of general quality equivalence outside these fixtures.

## Artifacts

- Machine-readable run summary: `summary.json`
- OCR results: `ocr/results.json`
- Generated images: `library/<profile>/<fixture>.png`
- Legacy normalized baseline: `standardized-results.json`
