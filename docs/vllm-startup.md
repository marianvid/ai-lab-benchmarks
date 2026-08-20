# The vLLM start sequence

vLLM loads a model in 42 to 212 seconds where llama.cpp takes 3 to 11. Reading
the weights from disk is a small part of that, and for a multimodal model most
of the time goes on work that text-only use never benefits from.

The measurements below come from vLLM's own startup logs, taken in August 2026
on Gemma-4-26B-A4B NVFP4 with a 32 768-token context window. **They were taken
once and have not been repeated.**

## Where the 111 seconds went

| From | Duration | Phase |
|---:|---:|---|
| 0 s | 3 s | process start, arguments and configuration |
| 3 s | 11 s | importing torch and CUDA, building the engine configuration |
| 14 s | 4 s | engine initialisation, NCCL, GPU context |
| 18 s | 9.3 s | **reading the weights from disk** |
| 28 s | 1 s | placing the model on the card — 18.16 GiB |
| 29 s | 21 s | **profiling the multimodal path**: fake images and video pushed through the encoder |
| 50 s | 0.3 s | `torch.compile` — loaded from cache, not recompiled |
| 51 s | 2 s | memory profiling for the CUDA graph, sizing the KV cache (337 862 tokens) |
| 53 s | 4 s | kernel warm-up, FlashInfer autotune cache, CUDA graph capture |
| 58 s | 51 s | **multimodal warm-up** |
| 111 s | | the server answers |

**Disk is 9.3 seconds of 111.** Eight per cent. Faster storage would barely
change the total.

**Two multimodal phases take 72 of the 111 seconds.** vLLM pushes invented
images and audio through the model to measure how much memory those paths need.
For text work the result is never used.

## The flag that removes it

`--language-model-only`. Between the 111-second run and a 39-second one there is
exactly one difference in the arguments:

```
slow:  {..., 'gpu_memory_utilization': 0.9, 'max_num_seqs': 32}
fast:  {..., 'gpu_memory_utilization': 0.9, 'language_model_only': True, 'max_num_seqs': 32}
```

Everything else identical. The 72 seconds come from that flag alone.

| | full | text-only |
|---|---:|---:|
| reading the weights | 9.3 s | 9.1 s |
| engine initialisation | 28.9 s | 8.4 s |
| multimodal warm-up | 50.8 s | not run |
| **total** | **111 s** | **39 s** |

The weights are read at the same speed in both. The whole difference is
multimodal work.

vLLM says so itself, in the first line of the fast run:

```
All limits of multimodal modalities supported by the model are set to 0,
running in text-only mode.
```

The flag disables nothing special. It sets the per-modality input limits to
zero, so there is nothing left to profile or warm up.

An alternative, `--limit-mm-per-prompt image=0,audio=0`, should do the same
thing more explicitly. **It has not been tested here.**

## What text-only costs

It is not free. From the same logs:

| | full | text-only |
|---|---:|---:|
| KV cache available | 9.15 GiB | 7.79 GiB |
| tokens in KV cache | 337 862 | 318 120 |
| CUDA graph memory | 0.12 GiB | 0.53 GiB |

About **6% of KV cache capacity**, because the CUDA graph takes more room.
Throughput is unaffected — that was measured — but the memory cost was not
mentioned anywhere until now.

For a model still holding over 300 000 tokens of cache, 6% is a smaller price
than 72 seconds on every start. It is a trade, not a free win.

## The compile cache is a separate, larger effect

The log above shows `torch.compile took 0.31 s`, which means the compiled
kernels were loaded ready-made from cache. With that cache empty the phase
expands enormously.

Measured through [AI-Lab](https://github.com/marianvid/ai-lab): **first start after moving the working directory, 241
seconds. The next one, 47 seconds.**

That is the third large cost, and it is invisible in the map above because the
cache was already warm when those logs were taken. It is also the most likely
explanation for the cold-versus-warm gaps in [loading.md](loading.md), which
were not isolated.
