# Dead ends

Two things kept because they cost time and would cost it again: measurements
that were wrong, and a conclusion reached by reading documentation instead of
running anything.

Nothing here is current. Every figure in these two pages has either been
corrected or superseded, and the corrections are stated where they belong. They
are here as a record of how the wrong number looked at the time, which is the
part that is hard to reconstruct afterwards.

## [Measurements that lied](measurements-that-lied.md)

Seven cases where the output looked reasonable and was not, each with what it
looked like, what caused it, how it was caught, and the corrected figure.

| | What looked true | What was happening |
|---|---|---|
| 1 | A model scored 0.000 and answered nothing | it was thinking, and got cut off mid-thought |
| 2 | A context window was smaller than configured | the parallel slots were dividing it |
| 3 | A timing loop never ran | two clocks compared against each other |
| 4 | A translation failed to parse | a comma inside the answer |
| 5 | One configuration started 70% slower | it was the only one paying for a rebuild |
| 6 | 287 735 tokens per second of prompt reading | the engine was answering from its cache |
| 7 | A flag made vLLM slower to start | it invalidated the compile cache |

The rule at the end is the one worth keeping: **if the harness were broken in
the most likely way, would the output look exactly like this?**

## [A conclusion drawn from documentation](conclusions-that-were-wrong.md)

A day spent deciding TensorRT-LLM and SGLang were not worth adding, using
throughput figures published for other hardware. Both were run on this card
afterwards.

The headline held — **model support is the binding constraint, not speed** —
and no engine can load an architecture nobody has written code for. Two of the
specific claims did not hold. The measured version is
[the four-engine study](../engines-2026-08.md).

It is kept because the reasoning was sound and the conclusion was still partly
wrong, which is the interesting kind of mistake.
