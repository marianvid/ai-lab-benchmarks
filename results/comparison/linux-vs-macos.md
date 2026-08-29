# Linux vs macOS benchmark comparison

This report compares the published Linux and macOS runs without treating infrastructure incidents, unsupported formats or semantic misses as model execution failures. All figures are single-pass observations.

## Hardware and runtime

| Platform | Hardware | Runtime | Relevant limitation |
|---|---|---|---|
| Linux | AOOSTAR GEM12+ Pro, RTX PRO 4500 Blackwell 32 GB over OCuLink | CUDA 13, vLLM nightly, AI-Lab/ComfyUI | OCuLink affects loading, not resident inference. |
| macOS | MacBook Pro, Apple M3 Max, 40-core GPU, 128 GB unified memory | macOS 15.7.3, Python 3.11.7, MLX 0.32.2, ComfyUI 0.34.0, torch 2.13.0 | Current FLUX workflows used Apple MPS; legacy FP8 dequantization remains unsupported. |

## Direct comparisons

| Area | Matched workload | Linux | macOS | Conclusion |
|---|---|---|---|---|
| ASR | Whisper large-v3-turbo, identical 100-row Romanian FLEURS selection | WER 0.118776, CER 0.034498, 8.405 s, 113.735x real time | WER 0.117862, CER 0.033972, 39.933 s, 23.939x real time | Accuracy is effectively tied; Linux throughput is 4.751x higher. |
| Generation | SD 1.5, five identical fixtures | 5/5 execution, 0/5 semantic, 10/24 criteria, 1.782 s mean | 5/5 execution, 0/5 semantic, 10/24 criteria, 7.122 s mean | Same semantic result; Linux is 3.997x faster. |
| Generation | Qwen Image, five identical fixtures | 5/5 execution, 4/5 semantic, 23/24 criteria, 38.190 s mean | 5/5 execution, 5/5 semantic, 24/24 criteria, 1214.625 s mean | macOS gains one rubric pass; Linux is 31.804x faster. macOS used a different local runtime/weight stack. |
| Generation | Legacy `flux2-benchmark`, five identical fixtures | 5/5 execution, 4/5 semantic, 22/24 criteria, 49.717 s mean | 0/5 images, five runtime/format incompatibilities, zero OOM | No latency or quality comparison is valid; the macOS failure is an unsupported FP8 dtype, not a model failure. |
| Editing | Qwen Image Edit, three identical fixtures | 3/3 execution and semantic, 155.759 s mean | 3/3 execution, 2/3 semantic, 11/12 criteria, about 2511 s mean | Linux is about 16.1x faster and passes the label edit that caused a small unintended mug change on macOS. |
| OCR | `ocr-smoke` and `ocr-server`, eight checksum-pinned fixtures | 8/8 execution, 5/8 exact; mean CER 0.0219 and 0.0250 | 8/8 execution, 5/8 exact; mean CER 0.0219 and 0.0250 | Identical published accuracy on the shared fixtures; both platforms have zero model failures. |

## macOS-only current FLUX alternatives

The current Mac-compatible FLUX profiles are not direct Linux baselines because the named models and formats differ from the legacy Linux FP8 profile.

| Profile | Execution | Semantic | Mean latency | Interpretation |
|---|---:|---:|---:|---|
| FLUX.2 Klein 4B BF16 | 5/5 | 4/5, 22/24 criteria | 23.0 s | Interactive choice. |
| FLUX.2 Dev Q8_0 | 5/5 | 5/5, 24/24 criteria | 17 min 27 s | Preferred full-size Mac profile. |
| FLUX.2 Dev BF16 | 5/5 | 5/5, 24/24 criteria | 20 min 13 s | Full-precision reference. |

Q8_0 is 13.7% faster than BF16 on the identical Mac suite with the same semantic score. Klein is 52.7x faster than Dev BF16 by mean latency.

## Classification boundaries

- Genuine model failures: zero in the final current macOS generation, editing and OCR runs.
- OOM: zero on both platforms for all rows above.
- Runtime/model-format incompatibility: five legacy macOS FLUX FP8 cases only.
- Semantic failures describe artifact rubric misses, not execution failures.
- VAD, diarization and the unmatched Linux ASR profiles still have no direct macOS baseline.

## Sources

- Linux: `results/audio/asr/summary.json`, `results/images/summary.json`, `results/images/semantic-review.json`, `docs/audio-results.md`, `docs/images-ocr.md`
- macOS: `results/audio/macos/`, `results/images/macos/summary.json`, `results/images/macos/semantic-review.json`, `results/images/macos/ocr/results.json`, `results/images/macos/report.md`
