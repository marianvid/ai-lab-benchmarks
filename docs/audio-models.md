# Audio models

Seven ASR instances and one VAD instance are in scope. Revisions are pinned in
the deployment inventory; the short hash here connects a published result to
that inventory.

| Model | Engine | Weights | Revision / release | Licence | Romanian |
|---|---|---|---|---|---|
| Whisper large-v3 | vLLM | 3.09 GB safetensors | `06f233fe06e7` | Apache-2.0 metadata; upstream code MIT | yes |
| Whisper large-v3-turbo | vLLM | 1.62 GB safetensors | `41f01f3fe87f` | MIT | yes |
| Qwen3-ASR-0.6B | vLLM | 1.88 GB safetensors | `5eb144179a02` | Apache-2.0 | yes |
| Qwen3-ASR-1.7B | vLLM | 4.70 GB safetensors | `7278e1e70fe2` | Apache-2.0 | yes |
| Parakeet TDT 0.6B v3 | NeMo | 2.51 GB `.nemo` | `541d1f99c6b0` | CC BY 4.0 | yes |
| Canary 1B v2 | NeMo | 6.36 GB `.nemo` | `87bc52657add` | CC BY 4.0 | yes |
| Nemotron 3.5 ASR Streaming 0.6B | NeMo | 2.37 GB `.nemo` | `1c8deaecc64b` | OpenMDW 1.1 | **no** — checkpoint prompts expose English, Spanish and Chinese |
| Silero VAD | ONNX Runtime, CPU | package repository | 6.2.1 / `7e30209a3e90` | MIT | language-independent |

## Stored but not in the Romanian run

Qwen3 ForcedAligner 0.6B is stored for possible international use, but its
published language list does not include Romanian. Running it here would
produce a number without a supported interpretation, so it is not presented as
a Romanian alignment result.

Pyannote Speaker Diarization Community-1 has a commercial-compatible CC BY 4.0
licence but is gated: its terms must be accepted and a Hugging Face token made
available to AI-Lab. It remains pending. NVIDIA Sortformer 4-speaker v1 was
excluded because its checkpoint is CC BY-NC 4.0.

These are exclusions, not hidden failures. The result page covers every model
that was actually run.

---

[← index](../README.md) · [Audio method](audio-method.md) · [Audio results](audio-results.md)
