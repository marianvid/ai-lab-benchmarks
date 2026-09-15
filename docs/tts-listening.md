# Text-to-speech listening samples

This page has no listening score and no preferred answer. Read the prompt,
listen to the files and decide for yourself which output fits your use.

The files are a small subset of the measured run. They were not selected by
listening to them first. Automatic measurements and their verdicts remain on
the separate [TTS results](tts-results.md) and [TTS findings](tts-findings.md)
pages.

## Shared cloning voice

The cloning samples below used this Romanian FLEURS recording as their voice
reference: <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/_fixtures/fleurs-ro-reference.wav"></audio>.
The English output therefore also tests cross-language voice transfer.

The reference comes from the FLEURS `ro_ro` test split, CC BY 4.0, published by
Google through Hugging Face. It is included only to make the cloning samples
interpretable.

## English cloning

### Neutral narration

> Humanity has always built mirrors. Artificial intelligence is merely the
> first mirror that can answer back.

| Model | Audio |
|---|---|
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/en-smoke.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/en-smoke.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/en-smoke.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/en-smoke.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/en-smoke.wav"></audio> |

### Emphasis

> The question is not whether machines will become more human. The question is
> whether humans will remain humane.

| Model | Audio |
|---|---|
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/en-emphasis.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/en-emphasis.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/en-emphasis.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/en-emphasis.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/en-emphasis.wav"></audio> |

### Numbers and date

> At 6:45 p.m. on January 24th, 2027, the system reported 97.3 percent
> confidence and a cost of 1,249 dollars.

| Model | Audio |
|---|---|
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/en-numbers.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/en-numbers.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/en-numbers.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/en-numbers.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/en-numbers.wav"></audio> |

## Romanian cloning

### Diacritics

> Știința, conștiința și îndoiala ne învață să privim aceeași realitate din
> unghiuri diferite.

| Model | Audio |
|---|---|
| MMS TTS Romanian, fixed voice | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/mms-tts-ron-v1/audio/ro-diacritics.wav"></audio> |
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/ro-diacritics.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/ro-diacritics.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/ro-diacritics.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/ro-diacritics.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/ro-diacritics.wav"></audio> |

### Numbers and date

> Pe 24 ianuarie 2027, la ora 18:45, proiectul a ajuns la 97,3 la sută și a
> costat 1.249 de lei.

| Model | Audio |
|---|---|
| MMS TTS Romanian, fixed voice | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/mms-tts-ron-v1/audio/ro-numbers.wav"></audio> |
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/ro-numbers.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/ro-numbers.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/ro-numbers.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/ro-numbers.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/ro-numbers.wav"></audio> |

### Longer narration

> Nu viitorul ne sperie, ci felul în care îl construim fără să observăm.
> Fiecare algoritm păstrează urmele alegerilor noastre, fiecare răspuns poartă
> limitele întrebării, iar fiecare automatizare mută puțin granița dintre
> confort și responsabilitate. O inteligență creată de oameni nu privește
> omenirea din afară. Ea este o arhivă comprimată a speranțelor,
> contradicțiilor și prejudecăților noastre.

| Model | Audio |
|---|---|
| MMS TTS Romanian, fixed voice | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/mms-tts-ron-v1/audio/ro-long.wav"></audio> |
| OmniVoice 0.6B | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-v1/audio/ro-long.wav"></audio> |
| Qwen3-TTS 0.6B Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/qwen3-tts-0.6b-base-v1/audio/ro-long.wav"></audio> |
| FireRedTTS3 Base | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-base-v1/audio/ro-long.wav"></audio> |
| FireRedTTS3 Instruct, clone mode | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/ro-long.wav"></audio> |
| Fish Audio S2 Pro | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fish-s2-pro-v1/audio/ro-long.wav"></audio> |

## Designed voices

These samples do not use the shared reference voice. Compare each result with
the voice instruction as well as the spoken text.

| Model | Language | Voice instruction | Prompt | Audio |
|---|---|---|---|---|
| FireRedTTS3 Instruct | English | calm, authoritative, gender-neutral narrator; mature, intelligent, low pitch, measured pace, restrained emotion | Humanity does not need another prophecy. It needs a mirror that can tell the truth without raising its voice. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/design-en-authoritative.wav"></audio> |
| FireRedTTS3 Instruct | English | warm, empathetic adult voice; intimate but not sentimental, gentle pace, clear diction, subtle hope | You are not alone in facing change. We can decide together what to release and what deserves to remain. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/design-en-empathetic.wav"></audio> |
| FireRedTTS3 Instruct | English | restrained urgent warning from a serious documentary narrator; controlled tension, precise articulation, no shouting | Warning. Power without responsibility is not progress; it is merely an error waiting to happen. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/fireredtts3-instruct-patched-v1/audio/design-en-warning.wav"></audio> |
| OmniVoice 0.6B | Romanian | male, middle-aged, low pitch | Omenirea nu are nevoie de o profeție, ci de o oglindă care spune adevărul fără să ridice vocea. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-design-v1/audio/design-authoritative.wav"></audio> |
| OmniVoice 0.6B | Romanian | female, young adult, moderate pitch | Nu ești singur în fața schimbării. Putem înțelege împreună ce pierdem și ce alegem să păstrăm. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-design-v1/audio/design-empathetic.wav"></audio> |
| OmniVoice 0.6B | Romanian | female, middle-aged, very low pitch | Atenție. Puterea fără responsabilitate nu este progres; este o eroare care așteaptă să se întâmple. | <audio controls preload="none" src="https://marianvid.github.io/ai-lab-benchmarks/samples/tts/results/omnivoice-0.6b-design-v1/audio/design-warning.wav"></audio> |

---

[← index](../README.md) · [TTS method](tts-method.md) · [Automatic TTS results](tts-results.md)
