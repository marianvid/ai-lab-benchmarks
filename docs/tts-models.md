# Text-to-speech models

Five locally stored candidates are evaluated. They remain in AI-Lab's
benchmark storage; this pass does not promote any of them to core.

| Model | Role | Stored size | English | Romanian | Licence consequence |
|---|---|---:|---|---|---|
| Facebook MMS TTS Romanian | fixed Romanian voice baseline | 0.29 GB | no | explicit | CC BY-NC 4.0; evaluation/non-commercial only |
| OmniVoice 0.6B | multilingual cloning and constrained voice design | 3.27 GB | explicit | explicit among 600+ languages | checkpoint is CC BY-NC 4.0; code is Apache-2.0 |
| Qwen3-TTS 0.6B Base | voice cloning | 2.52 GB | explicit | not in the published language list | Apache-2.0 |
| FireRedTTS3 Base + Instruct bundle | cloning plus natural-language voice design | 20.78 GB | explicit | advertised | Apache-2.0 |
| Fish Audio S2 Pro | high-quality cloning | 11.01 GB | multilingual | multilingual claim, no dedicated Romanian guarantee used here | Fish Audio Research License; commercial use needs separate terms |

Weight revisions used by the run are recorded in the result manifest and raw
metadata. Runtime code is pinned as well. FireRed required a local compatibility
patch to its Instruct wrapper because the upstream return arity did not match
the current internal call; the patch is published under
`harness/tts/patches/`.

MMS is absent from the 100-case English pass because the stored checkpoint is
Romanian-only. It remains useful as a fast, fixed-voice Romanian baseline.

Qwen is intentionally retained in the Romanian smoke pass despite lacking
official Romanian support. That result measures what this exact deployment did,
not a claim of support. The serious English pass evaluates it inside its stated
language scope.

FireRed Base and FireRed Instruct are measured separately in cloning mode even
though they share one downloaded bundle. Instruct is also probed in voice-design
mode because distinct characters are central to the intended use.

---

[← index](../README.md) · [TTS method](tts-method.md) · [TTS results](tts-results.md)
