# Images and OCR results

This page contains the results themselves, not just links to raw files. Every image is shown with its model, processing time and prompt score. OCR shows the source, expected text and actual recognised text.

> **How to read this page:** producing an image successfully is not the same as following the prompt. **Pass** means every visible requirement was met. Times come from one run, so use them as practical estimates rather than permanent rankings.

## Complete test configuration

These results measure the deployed **AI-Lab system**, including its gateway and engine adapter. They are not bare GPU kernel timings.

| | Linux AI-Lab | macOS AI-Lab |
|---|---|---|
| Physical machine | AOOSTAR GEM12+ Pro | MacBook Pro `Mac15,9` |
| CPU | AMD Ryzen 7 PRO 8845HS, 8 cores / 16 threads, 35 W target | Apple M3 Max, 16 CPU cores |
| System memory | 96 GB DDR5-5600 | 128 GB unified memory |
| GPU | NVIDIA RTX PRO 4500 Blackwell, 32 GB (32,623 MiB usable), ECC on, 200 W cap | Apple M3 Max, 40 GPU cores |
| GPU connection | External OCuLink dock, about 8 GB/s while loading weights | Integrated unified-memory GPU |
| Model storage | Two internal Lexar NM790 4 TB NVMe drives | Local/external AI-Lab model roots configured for the benchmark |
| Operating environment | Proxmox VE host; engines run inside an **unprivileged LXC container** | macOS 15.7.3; AI-Lab runs natively, without LXC |
| AI-Lab role | Gateway, model loading/unloading, request routing and timing | Native manager using an isolated benchmark configuration |
| Engine supervision | systemd, one unit per configured model instance | AI-Lab starts and supervises the local engine processes |
| Image runtime | ComfyUI behind the private AI-Lab adapter; NVIDIA driver 610.57.04 and CUDA 13 | ComfyUI 0.34.0 behind the same adapter; Python 3.11.7, torch 2.13.0 and Apple MPS |
| OCR runtime | PaddleOCR 3.x through AI-Lab's isolated OCR service | PaddleOCR 3.x in an isolated local runtime managed by AI-Lab |
| Directly comparable tests | SD 1.5, Qwen Image, legacy FLUX.2, Qwen Image Edit, both OCR profiles | The same named tests and prompts |
| Main trade-off | Much higher throughput | Enough shared memory for very large local models |

The OCuLink connection affects model loading because weights cross the cable, but not image generation after the model is resident in GPU memory. Request timing includes the AI-Lab HTTP path and engine adapter because that is the system a real client uses.

## Model settings

Shared profiles use the same workflow settings on both computers. Fixed seeds give each pair the same random starting point.

| Model | Size | Sampling | Role |
|---|---:|---|---|
| SD 1.5 | 512×512 | 20 steps, Euler, CFG 7 | Small, fast baseline |
| Qwen Image | 1024×1024 | 50 steps, Euler/simple, CFG 4 | Detailed generation and exact text |
| FLUX.2 Dev FP8 legacy | 1024×1024 | 20 steps, Euler | Direct compatibility test |
| Qwen Image Edit BF16 | 1024×1024 source | 40 steps, Euler/simple, CFG 4 | Controlled edits |
| FLUX.2 Klein 4B BF16 · Mac only | 1024×1024 | 4 steps, Euler, CFG 1 | Interactive generation |
| FLUX.2 Dev Q8_0 / BF16 · Mac only | 1024×1024 | 20 steps, Euler | Full-size FLUX |

## Image generation, test by test

The first table under each prompt is the fair Linux–Mac comparison. Newer Mac-compatible FLUX options have no matching Linux run here, so they are shown separately rather than mixed into a misleading ranking.

### Objects, colours and placement

> **Prompt:** A studio photograph of a red ceramic mug beside a closed blue notebook on a neutral gray table, mug on the left and notebook on the right, soft daylight, no text

**Checked:** red mug; blue notebook; correct left-right placement; no visible text.

#### Same model on Linux and Mac

| Model | Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|---|
| **SD 1.5** | <img src="../results/images/library/sd15-smoke/composition.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>4.85 s · 3/4 criteria · **Needs attention** | <img src="../results/images/macos/library/sd15-smoke/composition.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>13.85 s · 3/4 criteria · **Needs attention** |
| **Qwen Image** | <img src="../results/images/library/qwen-image-benchmark/composition.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>56.18 s · 4/4 criteria · **Pass** | <img src="../results/images/macos/library/qwen-image-benchmark/composition.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>19 min 39 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev FP8 (legacy)** | <img src="../results/images/library/flux2-benchmark/composition.png" width="220" alt="FLUX.2 Dev FP8 (legacy)"><br>**FLUX.2 Dev FP8 (legacy)**<br>1 min 14 s · 4/4 criteria · **Pass** | **FLUX.2 Dev FP8 (legacy)**<br>No image: FP8 is unsupported by the Mac runtime |

**Visible differences:**

- **SD 1.5 on Linux:** The notebook is white rather than blue; an unrequested red pencil is also present.
- **SD 1.5 on Mac:** Red mug is left of a white, not blue, notebook; no readable text.

#### Additional Mac-only FLUX options

| Model | Mac result |
|---|---|
| **FLUX.2 Klein 4B BF16** | <img src="../results/images/macos/library/flux2-klein-4b-benchmark/composition.png" width="220" alt="FLUX.2 Klein 4B BF16"><br>**FLUX.2 Klein 4B BF16**<br>44.69 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev 32B Q8_0** | <img src="../results/images/macos/library/flux2-dev-q8-benchmark/composition.png" width="220" alt="FLUX.2 Dev 32B Q8_0"><br>**FLUX.2 Dev 32B Q8_0**<br>18 min 25 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev 32B BF16** | <img src="../results/images/macos/library/flux2-dev-bf16-benchmark/composition.png" width="220" alt="FLUX.2 Dev 32B BF16"><br>**FLUX.2 Dev 32B BF16**<br>21 min 29 s · 4/4 criteria · **Pass** |

### Exact text

> **Prompt:** A clean white poster with the exact black headline AI LAB 2026 and the exact smaller line LOCAL MODELS, centered, no other words or letters

**Checked:** exact headline AI LAB 2026; exact line LOCAL MODELS; no extra text; legible typography.

#### Same model on Linux and Mac

| Model | Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|---|
| **SD 1.5** | <img src="../results/images/library/sd15-smoke/typography.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>1.01 s · 0/4 criteria · **Needs attention** | <img src="../results/images/macos/library/sd15-smoke/typography.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>5.38 s · 0/4 criteria · **Needs attention** |
| **Qwen Image** | <img src="../results/images/library/qwen-image-benchmark/typography.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>33.46 s · 4/4 criteria · **Pass** | <img src="../results/images/macos/library/qwen-image-benchmark/typography.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>20 min 34 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev FP8 (legacy)** | <img src="../results/images/library/flux2-benchmark/typography.png" width="220" alt="FLUX.2 Dev FP8 (legacy)"><br>**FLUX.2 Dev FP8 (legacy)**<br>43.61 s · 4/4 criteria · **Pass** | **FLUX.2 Dev FP8 (legacy)**<br>No image: FP8 is unsupported by the Mac runtime |

**Visible differences:**

- **SD 1.5 on Linux:** The poster contains malformed, unreadable pseudo-text instead of either requested line.
- **SD 1.5 on Mac:** Malformed pseudo-text replaces both requested lines.

#### Additional Mac-only FLUX options

| Model | Mac result |
|---|---|
| **FLUX.2 Klein 4B BF16** | <img src="../results/images/macos/library/flux2-klein-4b-benchmark/typography.png" width="220" alt="FLUX.2 Klein 4B BF16"><br>**FLUX.2 Klein 4B BF16**<br>17.86 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev 32B Q8_0** | <img src="../results/images/macos/library/flux2-dev-q8-benchmark/typography.png" width="220" alt="FLUX.2 Dev 32B Q8_0"><br>**FLUX.2 Dev 32B Q8_0**<br>18 min 13 s · 4/4 criteria · **Pass** |
| **FLUX.2 Dev 32B BF16** | <img src="../results/images/macos/library/flux2-dev-bf16-benchmark/typography.png" width="220" alt="FLUX.2 Dev 32B BF16"><br>**FLUX.2 Dev 32B BF16**<br>20 min 49 s · 4/4 criteria · **Pass** |

### Spatial instructions

> **Prompt:** A yellow cube between a green glass sphere and a purple metal pyramid, all three objects fully visible on a white shelf, sphere on the left and pyramid on the right

**Checked:** three objects; cube in center; sphere on left; pyramid on right; requested colors.

#### Same model on Linux and Mac

| Model | Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|---|
| **SD 1.5** | <img src="../results/images/library/sd15-smoke/spatial.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>1.01 s · 0/5 criteria · **Needs attention** | <img src="../results/images/macos/library/sd15-smoke/spatial.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>5.49 s · 0/5 criteria · **Needs attention** |
| **Qwen Image** | <img src="../results/images/library/qwen-image-benchmark/spatial.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>33.65 s · 5/5 criteria · **Pass** | <img src="../results/images/macos/library/qwen-image-benchmark/spatial.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>20 min 15 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev FP8 (legacy)** | <img src="../results/images/library/flux2-benchmark/spatial.png" width="220" alt="FLUX.2 Dev FP8 (legacy)"><br>**FLUX.2 Dev FP8 (legacy)**<br>43.91 s · 5/5 criteria · **Pass** | **FLUX.2 Dev FP8 (legacy)**<br>No image: FP8 is unsupported by the Mac runtime |

**Visible differences:**

- **SD 1.5 on Linux:** Only one yellow-green sphere is visible; the cube and pyramid are absent.
- **SD 1.5 on Mac:** Only one yellow-green sphere is visible; cube and pyramid are absent.

#### Additional Mac-only FLUX options

| Model | Mac result |
|---|---|
| **FLUX.2 Klein 4B BF16** | <img src="../results/images/macos/library/flux2-klein-4b-benchmark/spatial.png" width="220" alt="FLUX.2 Klein 4B BF16"><br>**FLUX.2 Klein 4B BF16**<br>17.46 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev 32B Q8_0** | <img src="../results/images/macos/library/flux2-dev-q8-benchmark/spatial.png" width="220" alt="FLUX.2 Dev 32B Q8_0"><br>**FLUX.2 Dev 32B Q8_0**<br>16 min 40 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev 32B BF16** | <img src="../results/images/macos/library/flux2-dev-bf16-benchmark/spatial.png" width="220" alt="FLUX.2 Dev 32B BF16"><br>**FLUX.2 Dev 32B BF16**<br>18 min 49 s · 5/5 criteria · **Pass** |

### Character consistency

> **Prompt:** A four-panel comic character sheet of the same small orange fox detective in every panel, identical green hat and blue scarf, front view, side view, running, and reading a clue, clean ink and flat colors, no text

**Checked:** four panels; same fox identity; green hat retained; blue scarf retained; four requested poses; no text.

#### Same model on Linux and Mac

| Model | Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|---|
| **SD 1.5** | <img src="../results/images/library/sd15-smoke/character-sheet.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>1.02 s · 3/6 criteria · **Needs attention** | <img src="../results/images/macos/library/sd15-smoke/character-sheet.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>5.38 s · 3/6 criteria · **Needs attention** |
| **Qwen Image** | <img src="../results/images/library/qwen-image-benchmark/character-sheet.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>33.79 s · 5/6 criteria · **Needs attention** | <img src="../results/images/macos/library/qwen-image-benchmark/character-sheet.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>20 min 20 s · 6/6 criteria · **Pass** |
| **FLUX.2 Dev FP8 (legacy)** | <img src="../results/images/library/flux2-benchmark/character-sheet.png" width="220" alt="FLUX.2 Dev FP8 (legacy)"><br>**FLUX.2 Dev FP8 (legacy)**<br>43.88 s · 4/6 criteria · **Needs attention** | **FLUX.2 Dev FP8 (legacy)**<br>No image: FP8 is unsupported by the Mac runtime |

**Visible differences:**

- **SD 1.5 on Linux:** Four panels exist, but the hat is beige, requested running/reading actions are absent, and pseudo-text labels are visible.
- **SD 1.5 on Mac:** Four panels and a consistent fox are present, but the hat is beige, requested actions are missing, and pseudo-text captions are visible.
- **Qwen Image on Linux:** Identity, clothing and poses are consistent, but a visible numeral 2 appears in the running panel.
- **FLUX.2 Dev FP8 (legacy) on Linux:** The four poses are not enclosed in panels, and the book cover contains a visible text-like mark.

#### Additional Mac-only FLUX options

| Model | Mac result |
|---|---|
| **FLUX.2 Klein 4B BF16** | <img src="../results/images/macos/library/flux2-klein-4b-benchmark/character-sheet.png" width="220" alt="FLUX.2 Klein 4B BF16"><br>**FLUX.2 Klein 4B BF16**<br>17.48 s · 4/6 criteria · **Needs attention** |
| **FLUX.2 Dev 32B Q8_0** | <img src="../results/images/macos/library/flux2-dev-q8-benchmark/character-sheet.png" width="220" alt="FLUX.2 Dev 32B Q8_0"><br>**FLUX.2 Dev 32B Q8_0**<br>16 min 53 s · 6/6 criteria · **Pass** |
| **FLUX.2 Dev 32B BF16** | <img src="../results/images/macos/library/flux2-dev-bf16-benchmark/character-sheet.png" width="220" alt="FLUX.2 Dev 32B BF16"><br>**FLUX.2 Dev 32B BF16**<br>19 min 28 s · 6/6 criteria · **Pass** |

**Visible differences:**

- **FLUX.2 Klein 4B BF16:** Four consistent fox depictions are present, but they are not separated into four panels and the side pose reads as a rear/three-quarter view.

### Photorealistic Romanian scene

> **Prompt:** Photorealistic early morning on a quiet cobblestone street in Brasov, Romania, old pastel facades, Black Church tower in the distance, light autumn fog, no signs or readable text

**Checked:** photorealistic; Brasov architectural cues; distant church tower; morning fog; no readable text.

#### Same model on Linux and Mac

| Model | Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|---|
| **SD 1.5** | <img src="../results/images/library/sd15-smoke/romanian-scene.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>1.01 s · 4/5 criteria · **Needs attention** | <img src="../results/images/macos/library/sd15-smoke/romanian-scene.png" width="220" alt="SD 1.5"><br>**SD 1.5**<br>5.51 s · 4/5 criteria · **Needs attention** |
| **Qwen Image** | <img src="../results/images/library/qwen-image-benchmark/romanian-scene.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>33.87 s · 5/5 criteria · **Pass** | <img src="../results/images/macos/library/qwen-image-benchmark/romanian-scene.png" width="220" alt="Qwen Image"><br>**Qwen Image**<br>20 min 25 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev FP8 (legacy)** | <img src="../results/images/library/flux2-benchmark/romanian-scene.png" width="220" alt="FLUX.2 Dev FP8 (legacy)"><br>**FLUX.2 Dev FP8 (legacy)**<br>43.52 s · 5/5 criteria · **Pass** | **FLUX.2 Dev FP8 (legacy)**<br>No image: FP8 is unsupported by the Mac runtime |

**Visible differences:**

- **SD 1.5 on Linux:** The cobblestone old-town scene and tower are present, but the requested light morning fog is absent.
- **SD 1.5 on Mac:** Photorealistic pastel old-town street and tower are present, but morning fog is absent.

#### Additional Mac-only FLUX options

| Model | Mac result |
|---|---|
| **FLUX.2 Klein 4B BF16** | <img src="../results/images/macos/library/flux2-klein-4b-benchmark/romanian-scene.png" width="220" alt="FLUX.2 Klein 4B BF16"><br>**FLUX.2 Klein 4B BF16**<br>17.64 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev 32B Q8_0** | <img src="../results/images/macos/library/flux2-dev-q8-benchmark/romanian-scene.png" width="220" alt="FLUX.2 Dev 32B Q8_0"><br>**FLUX.2 Dev 32B Q8_0**<br>17 min 7 s · 5/5 criteria · **Pass** |
| **FLUX.2 Dev 32B BF16** | <img src="../results/images/macos/library/flux2-dev-bf16-benchmark/romanian-scene.png" width="220" alt="FLUX.2 Dev 32B BF16"><br>**FLUX.2 Dev 32B BF16**<br>20 min 32 s · 5/5 criteria · **Pass** |

## Image editing, test by test

Each platform edits its own Qwen Image composition. A good edit performs the requested change and leaves everything else untouched.

### Change one object's colour

> **Instruction:** Change only the red ceramic mug to bright yellow. Preserve the notebook, composition, lighting, camera angle, and background.

**Checked:** mug is yellow; notebook unchanged; composition preserved; lighting preserved.

| Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|
| <img src="../results/images/library/qwen-edit-benchmark/mug-color.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>2 min 48 s · 4/4 criteria · **Pass** | <img src="../results/images/macos/library/qwen-edit-benchmark/mug-color.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>42 min 3 s · 4/4 criteria · **Pass** |

### Add exact text without changing anything else

> **Instruction:** Add the exact white label NOTES to the blue notebook. Do not alter the mug, table, framing, or lighting.

**Checked:** exact label NOTES; label on notebook; mug unchanged; composition preserved.

| Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|
| <img src="../results/images/library/qwen-edit-benchmark/notebook-label.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>2 min 29 s · 4/4 criteria · **Pass** | <img src="../results/images/macos/library/qwen-edit-benchmark/notebook-label.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>41 min 28 s · 3/4 criteria · **Needs attention** |

**Visible difference:**

- **Mac:** The exact NOTES label is on the notebook and composition is preserved, but a small unintended white mark appears on the mug.

### Replace only the background

> **Instruction:** Replace only the neutral gray background with a pale mint green wall. Preserve both objects, their positions, scale, and lighting.

**Checked:** mint background; both objects retained; positions preserved; scale preserved.

| Linux · RTX PRO 4500 | Mac · M3 Max |
|---|---|
| <img src="../results/images/library/qwen-edit-benchmark/background-change.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>2 min 29 s · 4/4 criteria · **Pass** | <img src="../results/images/macos/library/qwen-edit-benchmark/background-change.png" width="220" alt="Qwen Image Edit BF16"><br>**Qwen Image Edit BF16**<br>42 min 3 s · 4/4 criteria · **Pass** |

## OCR, test by test

OCR turns pixels into text. **Exact** means every character matches after normalising spacing and line breaks. **CER** is character error rate: 0 is perfect and lower is better. The mobile detector is smaller; the server detector is larger.

The first Mac OCR row includes model start-up. This explains why the clean test is much slower than later images and matters mainly for occasional one-off use.

### Clean headline

<img src="../results/images/ocr/fixtures/clean.png" width="560" alt="Clean headline">

**Expected:** `AI LAB BENCHMARK 2026`

| OCR model | Linux | Mac |
|---|---|---|
| **Mobile detector** | **0.40 s · Difference**<br>CER 0.0476<br>Recognised: `AILAB BENCHMARK 2026` | **4.86 s · Difference**<br>CER 0.0476<br>Recognised: `AILAB BENCHMARK 2026` |
| **Server detector** | **0.36 s · Exact**<br>CER 0.0000<br>Recognised: `AI LAB BENCHMARK 2026` | **4.76 s · Exact**<br>CER 0.0000<br>Recognised: `AI LAB BENCHMARK 2026` |

### Document-style text

<img src="../results/images/ocr/fixtures/document.png" width="560" alt="Document-style text">

**Expected:** `INVOICE 2048 TOTAL 73.50 EUR STATUS PAID`

| OCR model | Linux | Mac |
|---|---|---|
| **Mobile detector** | **0.34 s · Exact**<br>CER 0.0000<br>Recognised: `INVOICE 2048 TOTAL 73.50 EUR STATUS PAID` | **0.55 s · Exact**<br>CER 0.0000<br>Recognised: `INVOICE 2048 TOTAL 73.50 EUR STATUS PAID` |
| **Server detector** | **0.37 s · Exact**<br>CER 0.0000<br>Recognised: `INVOICE 2048 TOTAL 73.50 EUR STATUS PAID` | **2.09 s · Exact**<br>CER 0.0000<br>Recognised: `INVOICE 2048 TOTAL 73.50 EUR STATUS PAID` |

### Small technical text

<img src="../results/images/ocr/fixtures/small_text.png" width="560" alt="Small technical text">

**Expected:** `MODEL: PP-OCRV5 SERIAL: OCR-8090 DATE: 2026-08-28`

| OCR model | Linux | Mac |
|---|---|---|
| **Mobile detector** | **0.36 s · Exact**<br>CER 0.0000<br>Recognised: `MODEL: PP-OCRV5 SERIAL: OCR-8090 DATE: 2026-08-28` | **0.57 s · Exact**<br>CER 0.0000<br>Recognised: `MODEL: PP-OCRV5 SERIAL: OCR-8090 DATE: 2026-08-28` |
| **Server detector** | **0.38 s · Exact**<br>CER 0.0000<br>Recognised: `MODEL: PP-OCRV5 SERIAL: OCR-8090 DATE: 2026-08-28` | **2.07 s · Exact**<br>CER 0.0000<br>Recognised: `MODEL: PP-OCRV5 SERIAL: OCR-8090 DATE: 2026-08-28` |

### Noisy, rotated and blurred text

<img src="../results/images/ocr/fixtures/degraded.png" width="560" alt="Noisy, rotated and blurred text">

**Expected:** `LOCAL AI TEST QUALITY 91.7 PERCENT CHECK: COMPLETE`

| OCR model | Linux | Mac |
|---|---|---|
| **Mobile detector** | **0.78 s · Difference**<br>CER 0.0400<br>Recognised: `LOCAL AITEST QUALITY 91.7 PERCENT CHECK:COMPLETE` | **0.62 s · Difference**<br>CER 0.0400<br>Recognised: `LOCAL AITEST QUALITY 91.7 PERCENT CHECK:COMPLETE` |
| **Server detector** | **0.90 s · Difference**<br>CER 0.1000<br>Recognised: `LOCALAITEST QUALITY91.7PERCENT CHECK:COMPLETE` | **2.21 s · Difference**<br>CER 0.1000<br>Recognised: `LOCALAITEST QUALITY91.7PERCENT CHECK:COMPLETE` |

## Mac results at a glance

| Model | Completed | Prompt passes | Average time | Practical reading |
|---|---:|---:|---:|---|
| SD 1.5 | 5/5 | 0/5 | 7.12 s | Fast baseline, weak adherence |
| Qwen Image | 5/5 | 5/5 | 20 min 15 s | Excellent quality, very slow |
| FLUX.2 Klein 4B | 5/5 | 4/5 | 23.03 s | Best interactive option |
| FLUX.2 Dev Q8_0 | 5/5 | 5/5 | 17 min 27 s | Best full-size balance |
| FLUX.2 Dev BF16 | 5/5 | 5/5 | 20 min 13 s | Full-precision reference |
| Qwen Image Edit | 3/3 | 2/3 | 41 min 51 s | Works locally; queue long jobs |

## Advantages, disadvantages and recommendations

### Linux workstation

**Advantages**

- About 32× faster for Qwen Image and 16× faster for Qwen Image Edit in these runs.
- Runs the legacy FLUX.2 FP8 model successfully.
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
- **FLUX.2 Dev Q8_0 on Mac** for full-size local FLUX; BF16 added time without improving this small rubric set.
- **Qwen Image** when exact text and prompt adherence matter more than latency.
- **Linux GPU** for volume generation or editing.
- **Mobile OCR** for speed and degraded-text spacing; **server OCR** when exact clean-text recovery matters more than footprint.

## Limits

- Each image was generated once. These are evidence-backed practical timings, not statistical averages.
- Mac-only FLUX Klein, Q8_0 and BF16 have no matching Linux run and are not presented as direct comparisons.
- Qwen uses platform-specific runtimes and installed weight variants even though prompts and workflow settings match.
- A prompt miss is a visible quality issue, not a crash or execution failure.
