# Text-to-speech method

This study asks whether locally hosted speech synthesis is good enough for a
Romanian-and-English narrated channel. It is a one-machine candidate-selection
study, not a general model leaderboard. The full raw audio stays on the private
AI-Lab host. The repository publishes the deterministic manifests, harness,
checksums, measurements and a small [listening subset](https://marianvid.github.io/ai-lab-benchmarks/docs/tts-listening.html).

## Two complementary passes

The bilingual smoke pass uses ten editorially written sentences: seven
Romanian and three English. Every cloning model receives the same nine-second
Romanian FLEURS enrollment recording. This deliberately stresses unsupported
cross-language cloning and makes the Romanian comparison controlled.

The serious English pass uses the official LibriTTS `test-clean` archive from
[OpenSLR](https://www.openslr.org/60/). Its downloaded archive SHA-256 is
`234ea5b25859102a87024a4b9b86641f5b5aaaf1197335c95090cde04fe9a4f5`.
The selection is deterministic and gender-balanced:

- five female and five male speakers;
- one enrollment recording per speaker, selected near eight seconds;
- ten different, held-out target utterances per speaker;
- 100 generated samples per model and 601.96 seconds of human target audio.

The enrollment sentence is never one of the target sentences. A model must
transfer speaker identity to text it has not heard in the reference audio.
`harness/tts/prepare_libritts.py` records source IDs, durations and SHA-256
hashes in a manifest. Dataset audio is not redistributed.

## What is measured

### Intelligibility

Whisper large-v3 transcribes every generated English file through the deployed
AI-Lab endpoint. WER and CER use Unicode normalisation, case folding,
punctuation removal and corpus-level edit counts. The same evaluator also
transcribes the original LibriTTS targets. That ground-truth pass measures the
evaluator's own floor; a generated model should not be judged against an
imaginary zero-error recogniser.

### Naturalness

[UTMOS22 strong](https://github.com/sarulab-speech/UTMOS22) predicts a mean
opinion score for every generated file and for the human recordings. It is a
useful consistent proxy, not a substitute for listening. In particular, a
cleanly spoken wrong sentence can receive a high MOS.

An earlier NISQA result remains in the raw directory for diagnosis only. The
available TorchMetrics checkpoint was the transmission-quality model rather
than the TTS naturalness checkpoint, so it is excluded from ranking.

### Voice identity

The local Pyannote/WeSpeaker VoxCeleb ResNet34-LM embedding compares each
generated file with both the enrollment audio and the held-out real target from
the same speaker. It also measures target-to-enrollment similarity. The latter
is the natural within-speaker reference for interpreting the generated scores.
Results are retained per speaker and gender so a good mean cannot hide a
systematic failure on one voice group.

### Operational cost

Generation time, output duration, real-time factor (RTF), process memory and
GPU memory are recorded per file where the runtime exposes them. RTF below one
means faster than real-time playback; RTF 5.7 means one minute of audio takes
about 5.7 minutes to generate.

## Reproducibility and limitations

All models see the same text and source audio, sequentially, on the RTX PRO
4500 Blackwell. The pass records exact weight revisions, runtime revisions,
settings and output hashes. The outputs are one seeded or default-inference
pass per case; stochastic variance is not measured.

LibriTTS is clean read English and differs from a finished editorial voice-over.
Automatic scores do not fully measure acting, pacing, emphasis, emotional
appropriateness, pronunciation of names, or long-form consistency. A finalist
therefore still needs a blinded listening test on the intended script style
and, before production cloning, a test using the owner's consented voice.

---

[← index](../README.md) · [TTS models](tts-models.md) · [TTS results](tts-results.md)
