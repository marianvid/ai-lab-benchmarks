<!-- tokenizer_intro -->
How many [tokens](glossary.md#token) the same content costs in each
language.

This is not a quality measurement and needs no GPU. It counts the
same 200 FLORES sentences — identical content in every language —
with `${model}`'s tokenizer.

<!-- token_notes -->

**The last column.** 1.50× means the same text costs half again as
many tokens as in English: a context window holds two thirds as much
of it, a request takes half again as long to read, and a hosted
model charges half again as much.

**The writing system does not predict the cost.** Chinese, in Han
characters, is the cheapest language here after English. The most
expensive is ${language}, written in ${script} — the same
alphabet as English.

What decides it is how much of that language the tokenizer was built
from. One trained mostly on English and Chinese text holds whole
Chinese words as single tokens and cuts Lithuanian into fragments.

A context window sized against
English documents holds about ${share} as much ${language}. Size it on the most expensive language you will
actually send, or requests will be rejected for length in a way that
looks like a model fault.
<!-- agentic_intro -->
A small controlled probe of a coding model acting through tools, not
just answering one isolated programming question. Each run receives a
throwaway repository, an architect document, file and test tools, and
up to 14 turns. Visible and hidden unit tests decide the result.

This is still a one-pass, four-task probe. It is useful evidence about
short agent loops, not proof that a model can maintain a large project.

<!-- agentic_findings -->

All three failed the same hidden edge case in `config-migration`: the
implementation correctly removed obsolete generated profiles and kept
user data, but omitted an empty `profiles` key when the input lacked
one. Protected architect, test and fixture files were unchanged.

Qwen3.8 therefore looked competent in the agent loop, but did not beat
the Qwopus control on correctness in this small pass. Q6 was faster and
smaller than Q8; Qwopus reached the same result more than twice as fast.

<!-- why_qwen38 -->
## Why Qwen3.8 can still feel better at coding

The aggregate standard score hides a split. Against Qwen3.6, Qwen3.8
Q6 solved two more HumanEval+ tasks and Q8 solved three more, while both
lost ground on the shorter, less structured MBPP+ descriptions. That is
consistent with a model that benefits more from an explicit contract and
structured task, even though the 541-problem total is tied or lower.

Qwen's full-precision model card reports larger generation-over-
generation gains on long-horizon coding: 73.0 versus 63.4 on Terminal
Bench and 61.7 versus 53.5 on SWE-bench Pro. Those published figures are
not scores for these GGUF
quantisations or this machine, but they support testing repository-level
agent work separately from HumanEval/MBPP rather than treating the latter
as the whole coding verdict: https://huggingface.co/Qwen/Qwen3.8-27B

Raw transcripts and the standard coding comparison are under
[`results/qwen38-agentic`](../results/qwen38-agentic/).
