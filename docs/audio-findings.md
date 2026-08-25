# Audio findings

## Accuracy and speed do not choose the same model

Canary 1B v2 produced the lowest Romanian error in this pass: **6.1% WER**. It
processed audio at **32× real time**, which is already ample for sequential
offline work but was the slowest successful entry.

Whisper large-v3 followed at **8.7% WER** and **46× real time**. Whisper
large-v3-turbo traded some accuracy for much more throughput: **11.9% WER** at
**114× real time**.

Parakeet TDT 0.6B v3 is the striking operational compromise: **12.1% WER** at
**143× real time**, the fastest successful ASR result. On a large archive where
perfect transcripts are not required for discovery, that may matter more than
the six-point accuracy gap to Canary.

| Likely priority | Candidate from this pass | Why |
|---|---|---|
| best transcript among those tested | Canary 1B v2 | lowest WER and CER |
| familiar, strong general baseline | Whisper large-v3 | second-best accuracy; broad ecosystem |
| high-volume first pass | Parakeet TDT 0.6B v3 | fastest ASR with WER close to Turbo |
| high-volume Whisper compatibility | Whisper large-v3-turbo | 2.5× large-v3's processing rate in this run |

## Model size did not predict Romanian accuracy

Qwen3-ASR improved substantially from 0.6B to 1.7B — WER fell from **39.2%**
to **20.6%** — but both trailed the Whisper and NeMo entries. The larger Qwen
was also slower here. A general multilingual claim is not a substitute for a
measurement in the language and audio domain actually being processed.

## Diacritics explain only part of the errors

Removing Romanian diacritics improves every WER, but it does not change the
ordering. Canary moves from 6.1% to 5.7%; Whisper large-v3 from 8.7% to 7.9%.
Qwen's gap remains large. The main differences are recognition errors rather
than punctuation or diacritics alone.

## Compatibility has to be tested, not inferred

Nemotron 3.5 ASR Streaming loaded correctly, then its own prompt dictionary
refused Romanian and listed English, Spanish and Chinese variants. That is a
useful result: the runtime works, but this checkpoint does not serve the target
language. It is reported as unsupported rather than assigned a meaningless
WER.

Canary exposed a subtler integration trap. Without explicit source and target
language prompts it translated Romanian speech into English, producing output
that looked fluent while scoring roughly 100% WER. The adapter now sends the
model's documented ASR prompt. Fluent output is not proof that an audio request
was configured correctly.

## Diarization: Sortformer won this synthetic Romanian pass

Both diarization systems completed all 120 Echo files. Sortformer obtained
**29.35% DER** versus **31.99%** for Pyannote Community-1, and was much faster:
**394×** versus **62× real time**. Its advantage was present both without
overlap (28.97% versus 30.64%) and with overlap (29.70% versus 33.23%).

The licence changes the operational conclusion. Sortformer is CC BY-NC 4.0,
so it is a useful research baseline but not a production candidate for a
commercial Beacon deployment. Pyannote is CC BY 4.0 and remains the deployable
candidate from this pair. Also, Echo is synthetic; neither score substitutes
for a test on council or committee recordings.

## What remains before choosing for Beacon

FLEURS is clean read speech. Beacon will encounter council chambers, remote
microphones, overlapping speakers, compression, music, names and political
vocabulary. The next useful study is not another broad model download; it is a
small, manually transcribed Romanian set sampled from those real sources.

Silero processed the 15.9-minute corpus at **179× real time** on CPU and failed
no requests. That establishes technical viability, not VAD accuracy, because
FLEURS has no speech-boundary labels. Diarization now has a reproducible
Romanian synthetic baseline; the next step is a small labelled set drawn from
Beacon's actual long-form sources.

---

[← index](../README.md) · [Audio method](audio-method.md) · [Audio results](audio-results.md)
