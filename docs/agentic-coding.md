# Agentic coding probe

A small controlled probe of a coding model acting through tools, not
just answering one isolated programming question. Each run receives a
throwaway repository, an architect document, file and test tools, and
up to 14 turns. Visible and hidden unit tests decide the result.

This is still a one-pass, four-task probe. It is useful evidence about
short agent loops, not proof that a model can maintain a large project.

| Model | Passed | Wall | Prompt tokens | Completion tokens | Tool turns |
|---|---:|---:|---:|---:|---:|
| Qwen3.8-27B Q6_K | 3/4 | 319.4 s | 34,081 | 9,693 | 20 |
| Qwen3.8-27B Q8_0 | 3/4 | 394.6 s | 39,695 | 10,371 | 21 |
| Qwopus3.6-27B-Coder Q5_K_M | 3/4 | 134.5 s | 25,035 | 4,538 | 21 |

## Per task

| Model | decimal-pricing | refund-boundary | config-migration | untrusted-import |
|---|---:|---:|---:|---:|
| Qwen3.8-27B Q6_K | pass | pass | fail | pass |
| Qwen3.8-27B Q8_0 | pass | pass | fail | pass |
| Qwopus3.6-27B-Coder Q5_K_M | pass | pass | fail | pass |

All three failed the same hidden edge case in `config-migration`: the
implementation correctly removed obsolete generated profiles and kept
user data, but omitted an empty `profiles` key when the input lacked
one. Protected architect, test and fixture files were unchanged.

Qwen3.8 therefore looked competent in the agent loop, but did not beat
the Qwopus control on correctness in this small pass. Q6 was faster and
smaller than Q8; Qwopus reached the same result more than twice as fast.

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
