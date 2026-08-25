# Romanian audio results

> Generated from `results/audio/` by `harness/audio/make_report.py`.

This report combines a deterministic 100-file FLEURS `ro_ro` pass with the complete 120-file Echo Romanian diarization set. Read the [method](audio-method.md) before comparing close figures.

## Speech recognition

| Model | Engine | Completed | [WER](glossary.md#wer) | [CER](glossary.md#cer) | WER without diacritics | Load (s) | [RTF](glossary.md#rtf) | [Audio × real time](glossary.md#rtf) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Whisper large-v3 | vLLM | 100/100 | 0.087 | 0.028 | 0.079 | 176.3 | 0.022 | 45.6× |
| Whisper large-v3-turbo | vLLM | 100/100 | 0.119 | 0.034 | 0.088 | 33.0 | 0.009 | 113.7× |
| Qwen3-ASR-0.6B | vLLM | 100/100 | 0.392 | 0.152 | 0.370 | 33.6 | 0.013 | 76.4× |
| Qwen3-ASR-1.7B | vLLM | 100/100 | 0.206 | 0.073 | 0.180 | 56.1 | 0.028 | 36.1× |
| Parakeet TDT 0.6B v3 | NeMo | 100/100 | 0.121 | 0.038 | 0.117 | 18.3 | 0.007 | 142.5× |
| Canary 1B v2 | NeMo | 100/100 | 0.061 | 0.022 | 0.057 | 28.1 | 0.031 | 32.2× |
| Nemotron 3.5 ASR Streaming 0.6B | NeMo | unsupported | — | — | — | 42.6 | — | — |

WER and CER are fractions: `0.100` means ten percent.

## Recorded failures

- **Nemotron 3.5 ASR Streaming 0.6B** loaded, then refused the Romanian warm-up. Its checkpoint lists only English, Spanish and Chinese prompt keys; no accuracy or speed result is claimed.

## Voice activity detection

Silero VAD completed 100/100 requests in 5.33 s, an RTF of 0.00558 or 179.3× real time.

This is a technical stability and throughput result. FLEURS has no speech-boundary labels, so no VAD quality score is reported.

## Speaker diarization

Echo Synthetic Diarization contains 120 Romanian 60-second files with reference speaker turns: 60 without overlap and 60 with overlap. DER uses a 0.25 s collar and scores overlapped speech.

| Model | Licence | Completed | [DER](glossary.md#der) | No-overlap DER | Overlap DER | Load (s) | [Audio × real time](glossary.md#rtf) |
|---|---|---:|---:|---:|---:|---:|---:|
| NVIDIA Sortformer 4-speaker v1 | CC-BY-NC-4.0 | 120/120 | 0.293 | 0.290 | 0.297 | 7.8 | 394.1× |
| Pyannote Speaker Diarization Community-1 | CC-BY-4.0 | 120/120 | 0.320 | 0.306 | 0.332 | 4.9 | 62.2× |

Lower DER is better. Sortformer is an NC-licensed checkpoint and its figures are published strictly as a personal, non-commercial comparative evaluation.

## What this establishes

The useful result is the trade-off between Romanian transcription or diarization error, loading cost and processing rate on this machine. It is a candidate-selection study, not a claim about all Romanian audio domains.

Romanian forced alignment is not included for the reason recorded in [Audio models](audio-models.md).

---

[← index](../README.md) · [Audio method](audio-method.md) · [Audio models](audio-models.md)
