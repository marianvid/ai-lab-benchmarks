# English speech and sound generation — results

Run date: 15 September 2026. These are single-run measurements on this
repository's [RTX PRO 4500 Blackwell machine](machine.md).

## Automatic speech results

| Model | Cases | UTMOS | Literal WER | RTF | Peak VRAM |
|---|---:|---:|---:|---:|---:|
| Qwen3-TTS 1.7B VoiceDesign | 11/11 | **4.345** | 3.73% | 1.029 | 4.62 GB |
| Qwen3-TTS 1.7B CustomVoice | 7/7 | 4.267 | 10.34% | 1.035 | 4.67 GB |
| Chatterbox Turbo 350M | 5/5 | 3.669 | **0.00%** | **0.217** | 4.99 GB |
| Dia2 2B | 3/3 | 3.140 | **0.00%** | 5.096 | 15.23 GB |

RTF is generation time divided by audio duration. Below 1.0 is faster than real
time. Model load time was 1.77 seconds for Qwen VoiceDesign, 1.85 seconds for
Qwen CustomVoice, 8.10 seconds for Chatterbox and is not comparable for Dia2
because its loader initializes lazily inside generation.

The Qwen literal WER values are dominated by the precision case. Removing only
that formatting-sensitive case gives 0.41% WER for VoiceDesign and 0.00% for
CustomVoice. VoiceDesign made one remaining word substitution; CustomVoice and
Chatterbox preserved all ordinary words in their tested scripts.

Model storage was 4.3 GB for each Qwen variant, 3.8 GB for Chatterbox Turbo,
and 7.2 GB for Dia2 plus 367 MB for its Mimi codec. These are measured disk
occupancies on this machine, not parameter-count estimates.

### Automatic verdicts

- **Quality and range:** Qwen3-TTS 1.7B VoiceDesign is the first candidate. It
  has the highest mean UTMOS and covers all requested accent, delivery, emotion
  and character descriptions without a cloned voice.
- **Repeatable built-in voices:** Qwen3-TTS 1.7B CustomVoice is close on UTMOS
  and preserves ordinary text perfectly here. Its Aiden whisper is its weakest
  UTMOS case, so VoiceDesign is the stronger expressive default.
- **Paralinguistic events and latency:** Chatterbox Turbo is much faster and its
  ordinary text survives intact. `chuckle` scores well; explicit laugh and cough
  reduce UTMOS. It is a useful specialist, not the quality winner in these
  measurements.
- **Dialogue experiment:** Dia2 is intelligible but slow and scores well below
  Qwen on UTMOS. It is not recommended as the default speech engine.

UTMOS does not verify whether “British”, “Indian English” or another requested
accent is correct. No automatic accent verdict is claimed. The generated files
and their exact instructions are on the [listening page](audio-synthesis-listening.html).

## Sound effects

TangoFlux completed 8/8 descriptions at 50 steps. It generated 67 seconds of
stereo audio in 26.33 seconds: weighted RTF 0.393. Peak VRAM was 8.21 GB, model
load was 89.31 seconds, and its benchmark storage occupies 6.8 GB.

CLAP text–audio cosine similarity was 0.275 mean, from 0.106 for quiet server
room ambience to 0.474 for the cinematic transition. This shows substantial
variation in prompt alignment; it is not enough to call the set
production-ready automatically.

The model's licence is the practical blocker: this TangoFlux release is marked
for research/non-commercial use. It demonstrates that local text-to-SFX is
technically realistic on this GPU, but it is not the recommended engine for a
commercial channel. Stable Audio 3 is not included because its gated licence
was not authenticated for these tests.

## Reproducibility

The complete raw JSON, evaluator output and hashes are in
[`results/audio-synthesis`](../results/audio-synthesis/) and
[`results/sound-effects`](../results/sound-effects/). The manifests and runners
are in [`harness/tts`](../harness/tts/) and
[`harness/soundfx`](../harness/soundfx/).
