# Images and OCR results

This page contains the results themselves, not just links to raw files. Every image is shown with its model, processing time and prompt score. OCR shows the source, expected text and actual recognised text.

> **How to read this page:** producing an image successfully is not the same as following the prompt. **Pass** means every visible requirement was met. Times come from one run, so use them as practical estimates rather than permanent rankings.

## Complete test configuration

These results measure the deployed **${ai_lab} system**, including its gateway and engine adapter. They are not bare GPU kernel timings.

| | Linux ${ai_lab} | macOS ${ai_lab} |
|---|---|---|
| Physical machine | AOOSTAR GEM12+ Pro | MacBook Pro `Mac15,9` |
| CPU | AMD Ryzen 7 PRO 8845HS, 8 cores / 16 threads, 35 W target | Apple M3 Max, 16 CPU cores |
| System memory | 96 GB DDR5-5600 | 128 GB unified memory |
| GPU | NVIDIA RTX PRO 4500 Blackwell, 32 GB (32,623 MiB usable), ECC on, 200 W cap | Apple M3 Max, 40 GPU cores |
| GPU connection | External OCuLink dock, about 8 GB/s while loading weights | Integrated unified-memory GPU |
| Model storage | Two internal Lexar NM790 4 TB NVMe drives | Local/external ${ai_lab} model roots configured for the benchmark |
| Operating environment | Proxmox VE host; engines run inside an **unprivileged LXC container** | macOS 15.7.3; ${ai_lab} runs natively, without LXC |
| ${ai_lab} role | Gateway, model loading/unloading, request routing and timing | Native manager using an isolated benchmark configuration on `${manager}` |
| Engine supervision | systemd, one unit per configured model instance | ${ai_lab} starts and supervises the local engine processes |
| Image runtime | ComfyUI behind the private ${ai_lab} adapter; NVIDIA driver 610.57.04 and CUDA 13 | ComfyUI 0.34.0 behind the same adapter; Python 3.11.7, torch 2.13.0 and Apple MPS |
| OCR runtime | PaddleOCR 3.x through ${ai_lab}'s isolated OCR service | PaddleOCR 3.x in an isolated local runtime managed by ${ai_lab} |
| Directly comparable tests | SD 1.5, Qwen Image, legacy FLUX.2, Qwen Image Edit, both OCR profiles | The same named tests and prompts |
| Main trade-off | Much higher throughput | Enough shared memory for very large local models |

The OCuLink connection affects model loading because weights cross the cable, but not image generation after the model is resident in GPU memory. Request timing includes the ${ai_lab} HTTP path and engine adapter because that is the system a real client uses.

## Model settings

Shared profiles use the same workflow settings on both computers. Fixed seeds give each pair the same random starting point.

| Model | Size | Sampling | Role |
|---|---:|---|---|
| SD 1.5 | 512×512 | 20 steps, Euler, CFG 7 | Small, fast baseline |
| Qwen Image | 1024×1024 | 50 steps, Euler/simple, CFG 4 | Detailed generation and exact text |
| FLUX.2 Dev FP8 legacy | 1024×1024 | 20 steps, Euler | Direct compatibility test |
| Qwen Image Edit BF16 | 1024×1024 source | 40 steps, Euler/simple, CFG 4 | Controlled edits |
| FLUX.2 Klein 4B BF16 · Mac only | 1024×1024 | 4 steps, Euler, CFG 1 | Interactive generation |
| FLUX.2 Dev Q8_0 / BF16 | 1024×1024 | 20 steps, Euler | Full-size FLUX, directly compared on both machines |

## Image generation, test by test

The first table under each prompt is the fair Linux–Mac comparison. FLUX.2 Klein remains Mac-only and is shown separately.${generation}

## Image editing, test by test

Each platform edits its own Qwen Image composition. A good edit performs the requested change and leaves everything else untouched.${editing}

## OCR, test by test

OCR turns pixels into text. **Exact** means every character matches after normalising spacing and line breaks. **CER** is character error rate: 0 is perfect and lower is better. The mobile detector is smaller; the server detector is larger.

The first Mac OCR row includes model start-up. This explains why the clean test is much slower than later images and matters mainly for occasional one-off use.${ocr}

## Mac results at a glance

| Model | Completed | Prompt passes | Average time | Practical reading |
|---|---:|---:|---:|---|${glance}

## Advantages, disadvantages and recommendations

### Linux workstation

**Advantages**

- About 32× faster for Qwen Image and 16× faster for Qwen Image Edit in these runs.
- Runs the legacy FLUX.2 FP8 model successfully.
- FLUX.2 Dev Q8_0 and BF16 both passed all 24 prompt criteria; Q8_0 is the practical upper-quality option.
- Qwen Image Edit passed all three preservation tests.
- Low, predictable OCR latency after the service is available.

**Disadvantages**

- Dedicated GPU memory is limited to 32 GB, so very large workflows depend on quantisation or offloading.
- SD 1.5 is fast but follows these detailed prompts poorly.

### MacBook Pro

**Advantages**

- Its 128 GB unified memory runs FLUX.2 Dev BF16, Dev Q8_0, Qwen Image and Qwen Image Edit without OOM.
- FLUX.2 Klein averages about 23 seconds and is the clear interactive choice.
- Dev Q8_0 and BF16 both passed all 24 criteria; Q8_0 was 13.7% faster.
- OCR quality is effectively identical to Linux on these fixtures.

**Disadvantages**

- Full-size generation takes roughly 17–20 minutes per image; Qwen editing takes roughly 42 minutes.
- The older FLUX.2 FP8 format is incompatible with the Mac runtime; use Q8_0 or BF16.
- OCR has a visible cold-start cost for occasional single images.

### What to choose

- **FLUX.2 Klein on Mac** for quick drafts and interactive work.
- **FLUX.2 Dev Q8_0 on either machine** for full-size local FLUX; Linux is much faster, while Mac avoids a separate GPU-memory ceiling.
- **Qwen Image** when exact text and prompt adherence matter more than latency.
- **Linux GPU** for volume generation or editing.
- **Mobile OCR** for speed and degraded-text spacing; **server OCR** when exact clean-text recovery matters more than footprint.

## Limits

- Each image was generated once. These are evidence-backed practical timings, not statistical averages.
- FLUX.2 Klein is Mac-only. Q8_0 and BF16 are direct Linux–Mac comparisons.
- Qwen uses platform-specific runtimes and installed weight variants even though prompts and workflow settings match.
- A prompt miss is a visible quality issue, not a crash or execution failure.
