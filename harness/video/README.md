# Video harness

This directory contains the reproducible inputs and small wrappers used by the
presenter-video pass. Model weights are intentionally not stored in Git.

`cases-v1.json` defines the three source portraits. The images generated from
those prompts are kept under `results/video/fixtures-v1`. The English speech
tracks are selected from `harness/tts/cases-english-v2.json` and are trimmed to
six seconds on the benchmark machine.

## Runners

- `run_echomimic_v3.py` configures the official preview runner, applies mmgp
  CPU/GPU offload and records CUDA allocator peaks.
- `run_measured.py` wraps a model command and polls process RAM, GPU memory and
  utilisation.
- `evaluate_video.py` samples frames and records face coverage, source-identity
  cosine, face geometry, sharpness and frame delta.
- `wan22-s2v-comfyui-api.json` is the native ComfyUI API workflow used for the
  Wan2.2-S2V FP8-scaled run. The model search paths point at complete benchmark
  storage; no model component is copied into core storage.

The Python dependencies for the last runner are pinned in
`requirements-evaluation.txt`.

## Compatibility patches

Patches under `patches/` are part of the method, not changes to AI-Lab:

- InfiniteTalk uses native PyTorch scaled dot-product attention because the
  available FlashAttention/xFormers kernels reject Blackwell compute
  capability 12.0.
- MuseTalk can use its face detector without importing the MMPose/MMCV stack,
  whose compiled operators are unavailable for this runtime. The fallback is
  intentionally reported with the result because it changes preprocessing.
- JoyVASA and LivePortrait Animals use the reference PyTorch implementation of
  XPose deformable attention. The custom CUDA extension cannot be built against
  the CUDA 12.8 PyTorch wheel on the CUDA 13 Blackwell host.
- HunyuanVideo-Avatar used a variable-length wrapper around native PyTorch SDPA
  when FlashAttention was unavailable. Transformers 4.45.2 preserved the LLaVA
  image-token expansion expected by the upstream inference code. The source
  patch is not redistributed because the model licence excludes the European
  Union, where the test machine is located.
- Wan2.2-S2V uses the native ComfyUI scaled-FP8 loader. An attempted DiffSynth
  compatibility path generated corrupted frames and is not part of the
  reported viewing set.

All model components, including auxiliary face and synchronization models,
remain together under the benchmark model root. Runtime cache paths contain
symlinks only, so no model is split between benchmark and core storage.
