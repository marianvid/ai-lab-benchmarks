# Glossary

Every column header in this repository links here. If a term in a table is
unclear, the link beside it lands on the entry below.

## Measurements

### Prefill
Also *prompt reading*. The engine turning your input text into the internal
numbers the model works with. It happens once per request, and all the tokens
can be processed together, so it is fast — thousands of tokens per second.

An agent that pastes whole files into every request spends most of its time
here.

### Decode
Also *generation*. The engine producing the answer, one token at a time. Each
token depends on the one before it, so it cannot be split up — tens of tokens
per second, not thousands.

A chat interface waiting for a reply is watching decode.

### TTFT
*Time to first token.* Seconds between sending the request and the first piece
of the answer arriving. On a long prompt this is essentially the prefill time,
and it is what a person experiences as "it is thinking".

### Concurrency
How many requests are in flight at the same time. In this repository it is set
explicitly: `c=8` means eight requests were sent and the engine handled them
however it chose to.

### Continuous batching
An engine's ability to add new requests to a batch that is already running, and
to release a slot the moment a request finishes.

vLLM does this. llama.cpp allocates a fixed number of slots at startup and
divides the context window between them, so a ninth request waits for one of
eight to finish.

This is the single largest difference between the two engines measured here.

### Wall / wall time
Seconds measured on a clock, start to finish, including everything: network,
queueing, the model thinking. Not CPU time.

### Items per second
Completed units of work per second of wall time — sentences classified,
questions answered, articles processed. Throughput as a person would count it.

## Scores

### F1
A single number between 0 and 1, higher better, combining two things:

- **Precision** — of the items the model said were X, how many were.
- **Recall** — of the items that were X, how many the model found.

F1 is their harmonic mean, which means it is low if either is low. A model
cannot score well by being cautious or by guessing freely.

**Why not accuracy.** The classification set here is 15% positive. A model that
answers "no" to everything is right 85% of the time and has found nothing: 0.85
accuracy, 0.00 F1.

**Undefined** when a slice contains no positive items at all — there is nothing
to find, so recall has no meaning. Reported as `—`, never as 0.

### Accuracy
The fraction answered correctly, 0 to 1. Useful when the possible answers are
balanced, misleading when they are not. Shown alongside F1 to make that visible.

### Chance level
What a model scores by guessing. On the comprehension task there are four
options, so chance is **0.25**. A score near 0.25 means the model did not read
the passage, whatever else it looks like.

### chrF++
A translation score from 0 to 100, higher better. It compares the model's
output with a reference translation by counting shared character sequences and
shared word pairs.

It needs no judge model and has no opinion, which is why it is used here.

Rough reading: below 40 is poor, 50–60 is usable, above 70 is close to the
reference. The absolute value depends heavily on which languages are in the
mix, so **compare only within one table**, never across studies.

### Pass rate
On the coding task, the fraction of problems whose generated code ran and
passed every test in the problem's own suite. Nothing partial and nothing
graded by opinion: it ran and passed, or it did not.

## Engines and formats

### llama.cpp
A C++ inference engine. Loads quickly, runs one or a few requests well, and
does not gain from having many requests at once.

### vLLM
A Python inference engine built around continuous batching and paged attention.
Slow to start — it compiles kernels for the specific model and card — and much
faster once many requests are arriving.

### GGUF
llama.cpp's file format, with the model's weights compressed to roughly 4 bits
each. One file, or a numbered set of files for a large model.

### NVFP4
A 4-bit floating-point format that Blackwell-generation NVIDIA cards handle in
hardware. Stored as a directory of `safetensors` files.

### Quantisation
Storing each weight in fewer bits than it was trained with, to make the model
smaller and faster, at some cost in quality. Both GGUF and NVFP4 above are
quantised to about 4 bits.

### KV cache
Short for *key-value cache*. Working memory the engine keeps for each request
in flight, proportional to how long that request's prompt and answer are.

It is why prompt length limits how many requests fit at once, and why the
throughput of long prompts and short prompts are different measurements.

### Context window
The maximum number of tokens a request may contain, prompt and answer together.
Set per instance. A larger window reserves more VRAM for the KV cache, so it
trades against how many requests fit at once.

### OCuLink
A cable standard carrying PCIe outside the case. The GPU here is in an external
dock connected this way rather than plugged into the motherboard.

It does not slow inference down — the weights sit in VRAM and are not moved —
but it does affect loading, and it is why splitting a model between card and
system memory is a bad idea on this machine.

## Data

### Token
The unit a model reads and writes: usually a few characters, sometimes a whole
word, sometimes one character. How text is cut into tokens depends on the
model's tokenizer, and the same sentence costs different numbers of tokens in
different languages.

### Cold start / warm start
**Cold** — the model's file has not been read recently, so the operating system
must fetch it from disk.

**Warm** — the file is still in the operating system's page cache in RAM, so
loading skips the disk entirely.

The difference can be several times over, which is why load times here are
reported as both.

### Page cache
Memory the operating system uses to keep recently-read files around. It is why
loading the same model twice in a row is faster the second time, and why a load
time quoted without saying which it was means very little.
