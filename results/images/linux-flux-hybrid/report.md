# FLUX.2 Dev hybrid VRAM/RAM benchmark on Linux

Tested on the AOOSTAR RTX PRO 4500 Blackwell host through AI-Lab and ComfyUI,
using the same five prompts, seeds, 1024×1024 resolution, twenty steps and
semantic rubric as the macOS image benchmark. Both endpoints used ComfyUI's
low-VRAM dynamic offload mode. The LXC memory limit was temporarily raised from
48 GiB to 80 GiB for BF16.

| Model | Complete bundle | Cases | Semantic result | Mean per image | Versus matching Mac run |
|---|---:|---:|---:|---:|---:|
| FLUX.2 Dev Q8_0 | 70.92 GB / 66.05 GiB | 5/5 | 24/24, 5/5 cases | 120.40 s | 8.70× faster |
| FLUX.2 Dev BF16 | 100.37 GB / 93.51 GiB | 5/5 | 24/24, 5/5 cases | 140.11 s | 8.66× faster |

The Q8_0 run took 116.65–133.50 seconds per image. BF16 took
130.83–175.83 seconds. BF16 was 16.4% slower on average and did not improve a
single rubric result in this matrix. This closely repeats the Mac outcome,
where both passed all criteria and Q8_0 was 13.7% faster.

Compared with the smaller Linux models already measured, Q8_0 is 2.42× slower
than FLUX.2 Dev FP8 mixed (49.72 s) and 3.15× slower than Qwen Image NVFP4
(38.19 s), but it closes the one-case semantic gap those models showed in the
fixed benchmark.

## Resource observations

- Q8_0 placed about 28.5 GB of the diffusion model on the GPU and offloaded
  about 5.3 GB. Observed process VRAM was roughly 27–29 GiB and container RAM
  use peaked around 23 GiB during the run.
- BF16 used roughly 30.8 GiB VRAM and 70–75 GiB container RAM. It ran
  successfully, but leaves little host headroom and therefore should not be a
  normal always-available endpoint on this machine.
- The large bundle size includes the common 35.58 GB Mistral text encoder and
  0.34 GB VAE in each self-contained model directory.

## Practical conclusion

Q8_0 is the useful upper-quality FLUX.2 endpoint for this host. It reproduces
the Mac benchmark's full semantic pass at about two minutes per image and does
not require the extreme RAM pressure of BF16. BF16 is a reference result rather
than a practical keeper unless a broader quality suite later finds an advantage.

This is one deterministic five-case pass. Equal rubric scores do not establish
general perceptual equivalence between Q8_0 and BF16.
