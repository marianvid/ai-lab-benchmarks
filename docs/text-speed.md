# Text speed on the Linux card: dense Qwen3.8-27B against MoE Qwen3.6-35B-A3B

Measured on 20 October 2026, 09:04–09:12 UTC. Raw numbers:
[`results/speed/2026-10-20-qwen38-nvfp4.json`](../results/speed/2026-10-20-qwen38-nvfp4.json)
and [`results/speed/2026-10-20-qwen36-nvfp4.json`](../results/speed/2026-10-20-qwen36-nvfp4.json).

## Words used here

- **Prefill:** the model reading the prompt. Measured in tokens per second.
- **Generation:** the model writing the answer, one token after another. Measured in tokens per second.
- **TTFT** (time to first token): from sending the request to receiving the first token of the answer. It includes any wait in the engine's queue.
- **Dense / MoE:** a dense model uses all its weights for every token. A mixture-of-experts (MoE) model uses only a few of its "experts" for each token. Qwen3.6-35B-A3B uses about 3 B of its 35 B parameters per token.
- **Pool:** vLLM's context cache, shared by all requests in flight. When it is full, extra requests wait inside vLLM.

## The models

| Instance | Model | Format | Context per request | At once | Pool |
|---|---|---|---:|---:|---:|
| `qwen38-nvfp4` | Qwen3.8-27B (dense) | NVFP4, vLLM, card share 0.93 | 32,768 | 16 | 130,389 tokens |
| `qwen36-nvfp4` | Qwen3.6-35B-A3B (MoE) | NVFP4, vLLM, card share 0.90 | 131,072 | 64 | 264,145 tokens |

The card is one NVIDIA RTX PRO 4500 Blackwell (32 GB). Each model was on the card alone.

## Method

- **Path:** every request went through the AI-Lab gateway, streamed, under one card reservation at priority 5 held for both models. No other calls reached the card during the run. vLLM's own log confirms it.
- **Prompts:** about 1,000, 4,000 and 15,000 tokens of plain English prose. Speed depends on the token count, not on the language. Each request starts with a unique line, so vLLM's prefix cache cannot reuse another request's work.
- **Answers:** exactly 256 tokens (`max_tokens` = `min_tokens` = 256), temperature 0.7, thinking off.
- **Concurrency:** 1, 4, 8 and 16 requests sent together, once per prompt size, after one warm-up request.
- **How each figure is computed:**
  - **Prefill alone** is prompt tokens divided by TTFT, at 1 request.
  - **Prefill total** is all prompt tokens divided by the slowest TTFT.
  - **Generation per request** is answer tokens after the first, divided by the time from the first token to the end. The median is shown.
  - **Generation total** is all answer tokens divided by the wall time.
- **Repeatability:** an earlier run at 08:54–08:59 gave the same figures within a few percent.

## One request

| | `qwen38-nvfp4` | `qwen36-nvfp4` |
|---|---:|---:|
| Prefill | ~5,200 tok/s | 10,400–13,300 tok/s |
| Generation | ~37–39 tok/s | ~190–215 tok/s |
| TTFT, 1k / 4k / 15k prompt | 0.20 / 0.73 / 2.87 s | 0.08 / 0.38 / 1.19 s |

## Under load

| Prompt × at once | `qwen38` wall | `qwen38` TTFT max | `qwen38` gen. total | `qwen36` wall | `qwen36` TTFT max | `qwen36` gen. total |
|---|---:|---:|---:|---:|---:|---:|
| 1k × 16 | 10.9 s | 2.6 s | 375 tok/s | 4.2 s | 1.0 s | 973 tok/s |
| 4k × 16 | 23.0 s | 10.6 s | 178 tok/s | 7.7 s | 4.1 s | 530 tok/s |
| 15k × 4 | 22.5 s | 14.2 s | 46 tok/s | 7.0 s | 4.7 s | 147 tok/s |
| 15k × 16 | 92.9 s | 84.9 s | 44 tok/s | 26.1 s | 23.2 s | 157 tok/s |

At 15k × 16, `qwen38` asks for about 239,000 tokens at once, but its pool holds 130,389. So about half of the requests wait inside vLLM, and the slowest waits 85 s before its first token. That is the mechanism behind the 504 timeouts ingest saw on 20 October with clusters of long Chinese batches.

## Reading it

- The MoE model is about **2–3× faster at reading** and about **5× faster at writing**, because it uses about 3 B parameters per token against 27 B.
- The dense model is the slower one, but it scored higher on news' Tag step: 77 % against about 65 % for the MoE models (news' own benchmark).
- **Choosing between them:** for volume (ingest's screening of thousands of articles), the MoE model's speed matters most. For a step where quality matters more than time, the dense model is worth its cost.
