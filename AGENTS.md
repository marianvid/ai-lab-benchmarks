# Working rules for this repository

This is the public benchmark of one AI-Lab machine. Its scripts are in
`harness/`, the raw results in `results/`, and the pages people read in `docs/`.
These rules apply to every agent working here, Claude included.

## 1. Write plainly

The owner is an experienced programmer, not a specialist in every field. Explain
words that belong to one niche (quantisation formats, CUDA, LXC, speech
metrics) the first time they appear; never explain general programming. Say
what a thing does before saying what it is called. Short sentences.

## 2. Every number on a page is generated

A results page is written by a generator from the committed raw results, never
typed. Change a page by changing its generator or its fixed text (in
`harness/textreport/prose/` and `harness/images/report-template.md`), then
regenerate it. The tests regenerate the published pages and fail if a single
byte differs.

## 3. Nothing about the machine is written into the code

Addresses, ports, folders and credentials come from AI-Lab's configuration,
read by `harness/shared/lab.py` from the file `$AI_LAB_CONFIG` names (its
`benchmark` section). A missing setting stops the script and names it. The one
literal allowed is the loopback address. This repository is public: private
values (the manager's real address, the Mac's paths) never enter it.

## 4. One copy of every result

A result lives here or in the private companion repository
(`ai-lab-benchmark-opts`, checked out at `opts/` and ignored here), never in
both. Work that cannot be published, and one-off tools made for a single run,
go there.

## 5. Small, tested modules

A function stays under 40 lines and a complexity of 10; a folder under 15
modules. Every module is imported by a test. A script that needs an engine's
own libraries (torch, an engine package) has a test that skips, naming the
library, where that library is missing.

## 6. Before a commit

In the `ai-lab` conda environment (`environment.yml`), from this folder:

    python -m pytest

The run enforces the coverage floor in `pytest.ini`, which only goes up. Then
the reviewer's gate for this project must pass. Nothing is committed or pushed
without the owner's go-ahead.
