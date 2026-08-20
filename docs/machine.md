# The machine

A home lab, not a server room. Everything measured here describes what a
single-GPU desktop-class machine does; the bottlenecks are that machine's.

## Hardware

| | |
|---|---|
| GPU | NVIDIA RTX PRO 4500 Blackwell, 32 GB (32 623 MiB usable) |
| GPU power cap | 200 W |
| ECC | on |
| Attachment | **OCuLink external dock**, PCIe address `01:00.0` |
| Driver | 610.57.04, CUDA 13 |
| Host | AOOSTAR GEM12+ Pro |
| CPU | AMD Ryzen 7 PRO 8845HS, 8 cores / 16 threads |
| CPU power target | 35 W, set in the BIOS |
| Memory | 96 GB DDR5-5600 |
| Model storage | internal NVMe (Lexar NM790) |

## The GPU is outside the machine

It sits in an external dock connected by an [OCuLink](glossary.md#oculink)
cable rather than in a motherboard slot. Three consequences, in order of how
much they matter:

**Inference is unaffected.** Once a model is loaded its weights are in VRAM and
stay there. Nothing crosses the cable while the model is answering, so none of
the throughput or quality figures in this repository are influenced by it.

**Loading crosses it.** Weights are copied from system memory to the card over
that link, so load times include it.

**Splitting a model across card and system memory is a bad idea here.** In that
arrangement data crosses the cable for every token generated. AI-Lab refuses the
configuration for that reason; what it costs is measured in
[loading.md](loading.md#a-model-larger-than-vram).

## Software

| | |
|---|---|
| Host OS | Proxmox VE |
| Engines run in | an unprivileged LXC container |
| llama.cpp | build b10447 |
| vLLM | 0.26.1rc1.dev949 (nightly) |
| Supervisor | systemd, one unit per model instance |

**The vLLM version looks older than it is.** Nightly builds take their version
number from the last release tag on the branch they were cut from, so
`0.26.1rc1.dev949` is newer than the `0.27.1` release. It was chosen because
the stable release would not load one of the models; see
[the vLLM bug](vllm-gemma4-bug.md).

## What is not here

An Apple M3 Max runs the same application. **Nothing in this repository was
measured on it.**
