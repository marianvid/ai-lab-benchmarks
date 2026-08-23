# Findings

Ten things this configuration turned out to do, each one traceable back to the
table it came from. Every number here appears in one of the measurement pages.

If you read nothing else, read the first three. They are about the choice
between the two engines, which turns out to matter far more than the choice
between models, and they explain when that stops being true.

## 1. The engine decides the speed. The model decides the quality.

The same model file can be run by either engine. When that is done, the answers
come out at the same standard and one engine is several times faster than the
other.

Two models were run both ways. The score column is F1, which measures how well
the model sorted sentences by whether they are about politics, on a scale where
1.0 is perfect. The speed column is how many sentences it got through per
second.

| Model | Engine | Classification F1 | Sentences/s |
|---|---|---:|---:|
| Gemma-4-26B-A4B | llama.cpp | 0.871 | 8.9 |
| Gemma-4-26B-A4B | vLLM | 0.875 | 51.1 |
| Qwen3.6-35B-A3B | llama.cpp | 0.895 | 8.0 |
| Qwen3.6-35B-A3B | vLLM | 0.889 | 53.6 |

Look at the pairs. The quality scores differ by 0.004 and 0.006, which is small
enough that running the test again could easily reverse it — this study treats
anything under 0.02 as the same number. The speeds differ by 5.7 and 6.7 times.

Same weights, same prompts, same card. Only the program running them changed.

**What follows from it.** If a model is producing answers you are happy with and
you want more of them per hour, changing the engine is the cheaper move. Changing
the model risks the quality you already have and, on this evidence, would not
help the speed nearly as much.

## 2. That speed only exists when requests arrive together

The gap in the first table is not something vLLM does to every request. It comes
from what happens when several requests are being handled at the same time.

Sending one request, waiting for the answer, then sending the next, the two
engines finish in about the same time. The difference appears when eight or
sixty-four requests are in flight at once. The table below is how much faster
each engine got when the load went from one request to sixty-four.

| Engine | Speed-up, 1 → 64 requests at once |
|---|---|
| vLLM | 7.2× – 16.4× |
| llama.cpp | 1.0× |

A gain of 1.0 means no gain at all: sixty-four requests took sixty-four times as
long as one.

The reason is in how the two programs reserve memory. llama.cpp decides at
startup how many requests it will handle simultaneously — call them slots — and
splits the available memory between them. Request number nine waits for a slot
to free up. vLLM keeps one shared pool instead and slides new requests into a
batch that is already running, so a request that finishes releases its share
immediately for whoever is next.

**What follows from it.** The vLLM figures describe a queue of work arriving in
parallel. A person typing one question at a time, or an agent that sends a
request and waits for the reply before sending the next, gets none of this.

## 3. Long prompts take most of that advantage back

The speed-up in finding 2 was measured on single sentences. Repeating the same
test with whole Wikipedia articles, of two to five thousand characters each,
gives a very different answer.

| Model | Engine | Speed-up on sentences | Speed-up on articles |
|---|---|---:|---:|
| Gemma-4-31B | vLLM | 16.4× | **1.3×** |
| Gemma-4-26B-A4B | vLLM | 13.9× | **1.4×** |
| Qwopus3.6-27B-Coder | vLLM | 13.6× | **1.5×** |
| Qwen3-Coder-30B-A3B | vLLM | 10.7× | **1.3×** |
| GLM-4.7-Flash | vLLM | 8.7× | **1.5×** |
| Qwen3.6-35B-A3B | vLLM | 7.2× | **1.5×** |
| every llama.cpp entry | llama.cpp | 1.0× | 1.0× |

Between seven and sixteen times on sentences. Between 1.3 and 1.5 on articles.
Every model, both engines, no exceptions.

There is a second detail in the underlying numbers. The whole gain arrives by
about the eighth simultaneous request, and after that nothing improves: eight,
thirty-two and sixty-four requests all finish at the same rate.

The explanation is memory. While a model is working on a request it has to keep
a running summary of everything it has read so far, which is called the
[KV cache](glossary.md#kv-cache) and lives on the graphics card alongside the
model itself. A long article needs far more of that space than a single
sentence, so far fewer requests fit on the card at the same time. Once the space
is full the rest simply wait their turn, and waiting is not throughput.

**What follows from it.** Size document work from the article numbers. The two
sets of figures differ by roughly a factor of ten, and the sentence numbers are
the flattering ones.

## 4. Load times mean nothing unless you say cold or warm

Starting a model twice in a row gives two very different numbers, because after
the first start the operating system is still holding the model's file in spare
memory. The second start skips the disk entirely.

The first column below is a genuine first read, taken after clearing that memory
deliberately. The second is a reload immediately afterwards.

| Model | Engine | Cold | Warm |
|---|---|---:|---:|
| Gemma-4-26B-A4B | vLLM | 212.4 s | 117.4 s |
| Qwen3.6-35B-A3B | vLLM | 177.0 s | 92.2 s |
| Qwopus3.6-27B-Coder | vLLM | 163.4 s | 69.1 s |
| Qwen3.6-35B-A3B | llama.cpp | 10.8 s | 5.3 s |
| Gemma-4-26B-A4B | llama.cpp | 9.0 s | 5.0 s |
| Gemma-4-E4B | llama.cpp | 3.9 s | 2.5 s |

A cold vLLM start costs roughly twice a warm one, and for the first model that
is a difference of 95 seconds — long enough to matter to anybody waiting.

What exactly fills those 95 seconds was not measured. It is some combination of
reading the model, reading vLLM's own installation, which runs to several
gigabytes, and rebuilding the collection of compiled routines it keeps on disk.
The gap is inconsistent between models of similar size, which rules out the disk
being the whole story.

**What follows from it.** If models sit on disk between uses, the cold column is
the one that applies to you. If the same model is loaded and unloaded through
the day, the warm one is.

## 5. llama.cpp starts in seconds, vLLM in minutes

Three to eleven seconds against forty-two to two hundred and twelve. For a job
that loads a model, asks it one question and shuts it down again, llama.cpp has
finished before vLLM has finished starting.

The crossover is around ninety seconds of continuous batched work. Below that,
vLLM spends longer starting than it saves. Above it, the throughput from
finding 2 has repaid the wait.

## 6. A model trained for code is a poor model for language

Qwen3-Coder-30B-A3B reads prompts faster than anything else measured here, and
comes last on every task involving language.

| | Best in the set | Qwen3-Coder-30B |
|---|---:|---:|
| Classification F1 | 0.906 | **0.726** |
| Translation chrF++ | 56.12 | **45.38** |
| Comprehension | 0.915 | 0.847 |
| Coding pass rate | 0.834 | 0.791 |

The chrF++ column measures how closely a translation matches one produced by a
person, counted in shared runs of characters, on a scale to 100.

The last row is the interesting one. It is not even the best programmer in the
set. Gemma-4-26B-A4B, which is a general-purpose model with no particular claim
to code, passes more of the Python problems.

**What follows from it.** Its usefulness here is narrow and real: it reads
prompts faster than anything else, which suits a job that has to get through a
lot of input. Keep it away from prose.

## 7. Size shows up in comprehension and almost nowhere else

Gemma-4-E4B is 4.3 GB on disk. The leading models are sixteen to twenty-two.
That is a large difference, and it does not show up evenly.

| | E4B (4.3 GB) | Best in the set |
|---|---:|---:|
| Classification F1 | 0.828 | 0.906 |
| Coding pass rate | 0.765 | 0.834 |
| Comprehension | **0.760** | **0.916** |

On classification and coding the small model is within eight points of the best
in the set, which for a quarter of the size is a good trade. On comprehension it
is 15.6 points behind.

That gap is larger than it looks. The comprehension test is a choice between
four answers, so a model that answered at random would score 0.25 without
understanding anything. Subtracting that floor, the small model is 0.51 above
guessing and the best is 0.66 — a third more.

Comprehension is where a small model runs out. Sorting a sentence by topic can
often be done from a keyword or two. Answering a question about a passage
requires holding the passage.

## 8. A context window holds less text in some languages than others

Models do not read letters, they read *tokens*, which are chunks of text of
varying size. How many tokens a sentence costs depends on the language it is
written in, and the differences are large.

The figures below are for identical sentences, translated, measured against the
English version.

| | |
|---|---|
| Chinese (Han) | 1.12× |
| Japanese | 1.24× |
| Hindi (Devanagari) | 1.31× |
| Russian (Cyrillic) | 1.40× |
| Ukrainian (Cyrillic) | 1.64× |
| Thai | 1.65× |
| **Lithuanian (Latin)** | **1.66×** |

The obvious explanation would be the writing system, and it is wrong. Chinese,
which shares no alphabet with English, is the cheapest language measured after
English itself. The most expensive one uses the same twenty-six letters.

What actually decides it is how much text in that language was used when the
tokenizer was built. A language the builders had plenty of gets efficient
chunks. A language they had little of gets broken into fragments.

**What follows from it.** The context window is the largest amount of text a
model will accept in one request, counted in tokens. An 8 192-token window holds
about 60% as much Lithuanian as English. A limit chosen by testing on English
documents will start rejecting Baltic or Thai text as too long, and it will look
like a fault in the model when it is arithmetic.

## 9. A model too large for the card still runs, on llama.cpp

A 46.2 GB model on a 32 GB card, generating 56.4 tokens per second, with the
part that does not fit held in ordinary system memory and reached over the cable
as needed.

There is one trap in setting it up. llama.cpp can work out for itself how many
layers of the model will fit, and it does that well. Give it a number instead
and it will use that number without checking, then fail trying to allocate 34 GB
on a 32 GB card. Leave the setting alone.

This works on llama.cpp because of how it splits the job: it sends the
calculation to wherever the data already is. vLLM does the opposite and moves
the data to the calculation, which on this machine means pushing it across an
[OCuLink](glossary.md#oculink) cable that is several times slower than the card's
own memory. The same arrangement is unusable there. See
[Configuration](machine.md).

**The cost falls unevenly, and that is the part worth knowing.** Across four
sizes of the same model, the speed of reading a prompt fell by 9.5 times as
layers moved off the card, while the speed of writing the answer fell only
twofold. Worse, 60% of the prompt-reading loss came from the first four layers
evicted. A model that fits with nothing to spare behaves nothing like one that
misses by five gigabytes. See
[What partial offload costs](partial-offload.md).

## 10. Doing eight times the arithmetic buys one improvement

Most models here are *mixture-of-experts*: they contain many specialised
sections and use only a few of them for any given word, so a 26-billion
parameter file does the work of a much smaller one on each token. Gemma-4-31B is
*dense*, meaning all thirty-one billion of its parameters are used every time.

The comparison below is as close to controlled as this set allows. Same family,
same maker, near-identical size on disk, both engines. The only real difference
is that the second model does roughly eight times the arithmetic per word.

| | 26B-A4B | 31B dense | 26B-A4B | 31B dense |
|---|---:|---:|---:|---:|
| Engine | llama.cpp | llama.cpp | vLLM | vLLM |
| Classification F1 | 0.871 | 0.877 | 0.875 | 0.883 |
| Comprehension | 0.884 | **0.916** | 0.873 | **0.914** |
| Translation chrF++ | 56.12 | 56.38 | 55.80 | 56.01 |
| Coding pass rate | **0.834** | 0.826 | 0.826 | 0.828 |
| Classification, sentences/s | **8.94** | 2.24 | **51.13** | 18.18 |

**Three of the four quality scores stay where they are.** Classification,
translation and coding all move by less than the 0.02 that counts as noise here,
and coding actually goes slightly the wrong way on llama.cpp. Comprehension is
the exception, gaining about 0.03 on both engines — the same task where the
small model in finding 7 lost the most, which is consistent.

**The bill is three to four times the wall clock.** The classification run goes
from 456 seconds to 1 823 on llama.cpp, and from 80 to 224 on vLLM. Generating
an answer drops from 101.9 tokens a second to 25.5.

**Batching is unaffected.** Between one request and sixty-four the dense model
goes from 2.9 to 47.8 sentences a second, a gain of 16.4 times, which is the
largest in the whole table. Being dense costs speed on each individual request
and does nothing to stop the engine packing more of them onto the card.

So the trade is exactly what it appears to be: three to four times longer, in
return for one measurable improvement, on one task.

## Choosing

A summary of the above, arranged by what you are trying to do.

| If you are doing this | Use | Because |
|---|---|---|
| Bulk multilingual work, short prompts, many at once | Gemma-4-26B-A4B on vLLM | 0.875 F1 at 51 sentences a second, and 13.9× from running requests in parallel |
| The same work on whole documents | Gemma-4-26B-A4B on vLLM | still the fastest, but expect around 13 articles a second rather than 120 — parallelism only buys 1.4× on long prompts, for every model here |
| Best answers, speed secondary | Qwopus3.6-27B-Coder on vLLM | 0.906 F1 and 0.915 comprehension, at about a third of the throughput |
| One question at a time | any model on llama.cpp | it will have answered before vLLM has finished starting |
| Getting through a lot of input quickly | Qwen3-Coder-30B-A3B | reads prompts faster than anything else here; keep it away from prose |
| Already running Qwen3.6-35B and wanting more speed | change the engine before you change the model | 13× the throughput under load, at a cost of 0.006 F1 |

## What this does not tell you

Four limits worth holding on to while reading any of the above.

**Every figure comes from a single run.** Nothing was repeated and averaged, so
there is no way to say how much a number would move if the same test ran again.
Treat differences under 0.02 F1 as no difference at all.

**Every measurement is one question and one answer.** Nothing here sends a
follow-up. That leaves out how a model behaves inside an agent that goes back
and forth twenty times over the same code, or in a conversation whose history
keeps growing, and both of those work the engine quite differently.

**Twenty languages, all of them well-resourced.** Nothing here says anything
about languages with little text on the internet, which is exactly where models
differ from each other most.

**The quality tasks ran with a context window of 8 192 tokens**, while the
latency and long-document measurements ran at 32 768. Each page says which
applied to it. Do not put a speed from one beside a speed from the other and
treat them as the same measurement.
