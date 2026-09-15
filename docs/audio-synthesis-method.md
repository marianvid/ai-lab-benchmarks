# English speech and sound generation — method

This pass replaces the withdrawn mixed-language TTS experiment. It tests only
natural English synthesis. No Romanian reference voice is reused, translated or
used to condition an English output.

The machine is the same [RTX PRO 4500 Blackwell system](machine.md) used by the
rest of this repository. Each result is one deterministic run. It is useful for
sizing this machine and screening models, not for establishing a general model
ranking.

## Speech cases

The controlled speech set contains eleven short scripts:

- American documentary narration;
- contemporary southern-British editorial narration;
- Indian English explanation;
- informal Black American conversation, requested as restrained and natural,
  with no imitation of a named person and no caricature;
- a close whisper;
- restrained grief, controlled warning and quiet wonder;
- an animated fantasy sidekick and an older Irish storyteller;
- names, dates, money, version numbers and an alphanumeric code.

[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) VoiceDesign receives the text
and the complete voice description. Qwen3-TTS CustomVoice uses its native
English Aiden and Ryan voices with a
delivery instruction. Chatterbox Turbo uses a 7.94-second native-English
LibriTTS reference and five separate scripts containing its supported
paralinguistic syntax. Dia2 uses three two-speaker dialogue scripts and the
official prefix voices.

The exact manifests and runners are in [`harness/tts`](../harness/tts/). Seeds,
durations, hashes, software versions, peak memory and per-case timing are in
[`results/audio-synthesis`](../results/audio-synthesis/).

## Automatic speech checks

UTMOS22 strong is used as a no-reference naturalness predictor. It is a useful
screening signal, not a listening judgment and not proof that the requested
accent or emotion was produced.

Whisper large-v3 transcribes every generated file. Word error rate (WER) checks
whether the words survived synthesis. The precision script is also reported
separately because Whisper writes spoken dates, money and codes in normalized
forms such as `February 19th`, `$14,805.60` and `AZ942`. Those are semantic
matches but literal string mismatches.

## Sound-effect cases

Eight English descriptions cover ambience, wet footsteps, precise tabletop
Foley, a spacecraft interface, a mechanical lock, indoor storm ambience, a
small nonverbal creature and a cinematic transition. TangoFlux runs for 50
steps at its default guidance scale. Files are stereo PCM WAV at 44.1 kHz.

CLAP cosine similarity compares each description with its generated audio in a
shared embedding space. Higher means closer *within this set*; it is not a
calibrated quality score and does not prove that every event occurred in the
requested order.

Stable Audio 3 small-sfx and medium were planned but not measured: both model
repositories required authenticated acceptance of their gated licence on this
machine. The harness records no fabricated substitute result.

## Listening material

The [listening page](audio-synthesis-listening.html) presents the exact input
beside every generated file. It assigns no listening score. The reader can play
the file and compare it with the text or sound description directly.

## Licences

| Model | Licence relevant to this pass |
|---|---|
| Qwen3-TTS 1.7B VoiceDesign / CustomVoice | Apache-2.0 |
| [Chatterbox Turbo](https://github.com/resemble-ai/chatterbox) | MIT; generated files contain its PerTh watermark |
| [Dia2 2B](https://github.com/nari-labs/dia2) | Apache-2.0 |
| [TangoFlux](https://github.com/declare-lab/TangoFlux) | research/non-commercial restrictions, Stability AI Community terms and training-data conditions |

TangoFlux is therefore an experiment here, not a production recommendation.
See each upstream model card and licence before using generated material.
