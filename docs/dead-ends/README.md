# Dead ends

This folder holds the two parts of the work that produced nothing usable. One is
a list of measurements that turned out to be wrong after they had already been
believed for a while. The other is a day spent deciding which inference engines
were worth adding, on the basis of numbers published for other people's
hardware, before anything had been run here.

Neither is current. Every figure in them has since been corrected or replaced,
and the corrected version is linked from each. They are kept because the useful
part of a mistake is what it looked like before anyone noticed, and that is
exactly the part that disappears once it has been fixed. A corrected benchmark
tells you the right answer. It does not tell you that the wrong answer looked
completely reasonable for two days.

## How the errors were actually found

None of them were found by re-reading the harness code. Every single one came
out of looking at something the summary score had hidden: the raw text the model
returned, the engine's own log, the shape of a tensor, or the wall clock.

The pattern repeated often enough to be worth stating. A number arrives. It is
plausible, or it is strange in a way that has an easy explanation ready. The
score is what gets looked at, because that is what the harness prints in bold.
Then something forces a look at the layer underneath, and the explanation that
had seemed obvious turns out to describe nothing that happened.

The most recent one was caught by nothing more sophisticated than disbelief. The
throughput table said the card was reading 287 735 tokens of prompt per second,
and the reaction to that was "these numbers seem suspiciously large". They were.
Working out why took an afternoon; noticing took a second, and no tooling at all.

## [Measurements that lied](measurements-that-lied.md)

Seven of them, each written up with what it looked like at the time, what was
really going on, how it came to light, and what the figure became once it was
fixed.

| | What the numbers said | What was really happening |
|---|---|---|
| 1 | A model answered nothing at all and scored 0.000 | it was thinking, and the answer limit cut it off before it finished |
| 2 | A context window was smaller than the one configured | the parallel slots were quietly dividing it between them |
| 3 | A timing loop finished without ever running | it compared two different clocks against each other |
| 4 | A translation could not be parsed | there was a comma inside the answer |
| 5 | One configuration started 70% slower than the others | it was the only one paying for a recompilation |
| 6 | The card read 287 735 tokens of prompt per second | the engine was answering out of its cache |
| 7 | A flag made vLLM slower to start | changing it threw away the compiled-kernel cache |

Two of these deserve reading in full rather than as a table row. The first one,
because a model that answers nothing looks broken and was in fact working
correctly, which is a failure mode worth recognising once. And the sixth,
because it survived a whole round of review, got published, and was then written
about in three separate pages as though it meant something.

The closing section is a checklist. The question that would have caught most of
them is whether the output would look exactly like this if the harness were
broken in the most likely way. The question that caught the sixth is different:
does the hardware have enough arithmetic in it to produce this number at all.

## [A conclusion drawn from documentation](conclusions-that-were-wrong.md)

A day went into working out whether TensorRT-LLM and SGLang were worth adding as
engines. The reasoning used throughput figures published by their authors,
measured on hardware that is not this hardware, and it concluded that neither
was worth the effort.

Both were run here afterwards. The main conclusion survived: what actually
decides whether an engine is usable is whether somebody has written code for the
model architecture you want to load, and the fastest engine in the world is no
use if it cannot read your weights. Two of the more specific claims did not
survive contact with the card. The measured version of all of it is in
[the four-engine study](../engines-2026-08.md).

It is kept for an uncomfortable reason. The reasoning in it is careful, the
sources are real, and the conclusion is still partly wrong, because the whole
thing was built on measurements taken somewhere else. A day of reading produced
a worse answer than an afternoon of running would have.
