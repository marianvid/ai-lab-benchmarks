# Text-to-speech findings

These are automatic benchmark verdicts. They apply to the test sets and the
machine described here.

## The English feasibility question is answered

All five cloning variants completed all 100 held-out English cases. Their WER
was between 2.81% and 3.57%; Whisper scored the original human recordings at
3.86% on the same transcripts. Every candidate therefore passes the automatic
intelligibility test for clean English narration.

This does not mean the synthetic voices are more human than the recordings.
Synthesised audio is unusually clean and regular, which helps both ASR and MOS
predictors. The human row is a calibration point, not a contestant.

## FireRed Base is the strongest voice clone

FireRed Base combined the lowest English WER (2.81%, tied with Fish) with the
best held-out speaker similarity (0.721). Natural target utterances from the
same speaker averaged 0.765 against the enrollment clip, so FireRed closed most
of the measurable identity gap. Its 95% speaker-bootstrap interval was
0.689–0.752.

It ran at 0.754 RTF and used about 15.8 GB of process GPU memory. That is faster
than playback and comfortably inside the 32 GB card. Its Apache-2.0 licence is
also the clearest route among the strong bilingual candidates for a potentially
commercial channel.

The bilingual smoke pass points to the same choice:
FireRed Base obtained 8.0% Romanian WER and the best clone similarity to the
common Romanian reference (0.820). Its Romanian UTMOS was much weaker than its
English result, so the automatic benchmark does not rank it first for Romanian
naturalness.

## Qwen is the compact English quality candidate

Qwen3-TTS 0.6B produced the highest predicted English naturalness (4.428),
3.57% WER and 0.683 held-out speaker similarity. It used roughly 4.3 GB of
process GPU memory and ran around real time (1.021 RTF). On automatic English
metrics it is the best quality-per-resource result in this pass.

It is not a Romanian production candidate from this checkpoint. Romanian is
absent from the published language list, and the smoke run obtained 29.3% WER.
For an English-only character or a fast preview pipeline it remains highly
relevant.

## The largest model did not win the cloning task

Fish S2 Pro tied the best WER (2.81%) and reached 4.405 UTMOS, but its held-out
speaker similarity was only 0.624. Its 95% interval (0.581–0.668) did not
overlap FireRed Base's interval. It was also by far the slowest candidate:
5.666 RTF and about 20.4 GB process GPU memory. Ten minutes of output therefore
cost roughly 56–57 minutes of synthesis on this machine.

Fish is technically stable and produces high-quality English, but this test
does not justify its cost for faithful cloning. A longer or cleaner consented
reference could improve it; that is a new experiment, not a reason to ignore
the present result. Its research licence also requires separate commercial
terms before use on a monetised channel.

## OmniVoice is operationally excellent but licence-limited

OmniVoice completed the suite at 0.109 RTF with 2.93% WER, 4.298 UTMOS and
0.675 voice similarity, using about 3.1 GB process GPU memory. It was also the
best practical Romanian smoke result when balancing correctness, naturalness,
voice retention and speed.

The checkpoint is CC BY-NC 4.0. That makes it a valuable research and preview
baseline, not the safe default for a commercial or monetised publication.

## FireRed Instruct has two different stories

As an English clone, FireRed Instruct was intelligible and natural but retained
speaker identity poorly (0.622), so Base is the better cloning checkpoint.

As a voice-design model, however, the small English character probe produced
three distinct instructed personas with zero ASR word errors and 4.515 mean
UTMOS. That is promising for characters which do not need to imitate a real
speaker. The probe contains only three English samples, so the result is
provisional rather than a broad voice-design verdict. The Romanian voice-design
probe was unusable at 79.6%
WER despite clean-sounding output.

## Gender split and confidence

Every synthetic model scored lower speaker similarity for the five female
speakers than for the five male speakers. Because the direction is shared by
all models and the embedding baseline also varies substantially by utterance,
this may reflect the evaluator or selected speakers as well as synthesis. It is
recorded, not turned into a biological generalisation. Qwen also had a visible
English WER gap (2.52% female versus 4.57% male); the other models were closer.

The speaker-bootstrap intervals overlap for WER and most UTMOS comparisons.
Treat small differences in those columns as ties. The clearest separation is
FireRed Base's speaker retention over Fish and FireRed Instruct.

## Practical shortlist

| Use | Candidate | Status after this pass |
|---|---|---|
| faithful bilingual clone, commercially plausible | FireRedTTS3 Base | automatic winner for voice retention and Romanian correctness |
| compact, high-quality English synthesis | Qwen3-TTS 0.6B Base | strong; not Romanian-supported |
| English designed characters | FireRedTTS3 Instruct | provisional winner; only three designed-voice samples were run |
| fast bilingual research/preview | OmniVoice 0.6B | technically strong; NC checkpoint blocks commercial default |
| slow high-quality research comparison | Fish S2 Pro | usable English, but cost and weak clone retention do not win here |

No model is moved to core by this report. Storage selection remains a separate
operational decision.

---

[← index](../README.md) · [TTS method](tts-method.md) · [TTS results](tts-results.md) · [Listening samples](tts-listening.md)
