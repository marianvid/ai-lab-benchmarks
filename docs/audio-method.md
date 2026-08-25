# Romanian audio method

This is a one-pass system study of Romanian speech recognition on the same
RTX PRO 4500 used by the text measurements. It asks two questions: how closely
each model reproduces the reference transcript, and how quickly this deployed
AI-Lab/Data-Lab system processes the audio.

## Corpus and selection

The source is the official `ro_ro` test split of
[FLEURS](https://huggingface.co/datasets/google/fleurs), licensed CC BY 4.0.
The converted parquet is fetched directly from the publisher. Audio and
reference text are not committed here.

One hundred rows are selected at equal intervals over the complete test table:

```text
row(i) = floor(i × total_rows / 100), for i = 0..99
```

This is deterministic, covers the whole ordering rather than only its first
rows, and avoids choosing examples after seeing model output. Source rows and
FLEURS identifiers are recorded with the results.

## Audio preparation

Data-Lab extracts the embedded files and uses FFmpeg to create mono, 16 kHz,
signed 16-bit PCM WAV. The same files are sent to every model. Download,
conversion and storage time are not part of inference timing.

The request crosses the private network from Data-Lab to the AI-Lab gateway.
Each model is loaded explicitly, every file is sent sequentially, and the model
is unloaded afterwards. Request time includes HTTP transfer and the engine
adapter because the aim is to measure the system clients actually use.

The first selected file is sent once as a warm-up immediately after loading.
That response is recorded but discarded before scoring and timing, so one
engine's first-kernel setup is not mistaken for steady inference speed.

## Accuracy

Text is Unicode-normalised, case-folded, stripped of punctuation and collapsed
to single spaces. Romanian diacritics are retained in the primary scores.

- **WER** is total word insertions, deletions and substitutions divided by the
  total reference words.
- **CER** applies the same edit-distance calculation to characters.
- Both are also calculated after removing diacritics. These secondary figures
  show how much error is orthographic; they do not replace correct Romanian.

Errors are aggregated over the corpus rather than averaging per-file rates, so
a two-word clip does not count as much as a twenty-word clip.

## Speed and failures

Real-time factor is successful request time divided by corpus audio duration.
Below 1 means faster than real time. Its inverse is audio seconds processed per
wall-clock second.

Every load and request failure is written into raw JSON. Failed requests are
not silently removed from the success count. Accuracy is computed from
successful transcripts only and must be read beside that count.

Load time is the single observed startup in this run. The host page cache and
vLLM compile cache were not cleared between audio models, so this column is an
operational observation, not the controlled cold/warm comparison used by the
text loading study.

## VAD and diarization

FLEURS has transcripts but no speech-boundary or speaker-turn annotations.
Silero VAD therefore gets a transport, stability and speed measurement only;
no VAD accuracy number is claimed. Diarization waits for both a commercially
compatible model and a labelled Romanian multi-speaker corpus.

---

[← index](../README.md) · [Audio models](audio-models.md) · [Audio results](audio-results.md)
