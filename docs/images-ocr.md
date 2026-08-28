# Image generation, editing and OCR

This pass measures one fixed run on AI-Lab. Transport success and prompt adherence
are reported separately: an image can be generated successfully and still fail its
semantic rubric. Only cases that reached model execution count in model totals.

## Result

All 18 image jobs reached model execution and produced valid PNG files. Semantic review passed 11/18 cases and failed 7/18. Across individual rubric criteria, 67/84 passed.

| Profile | Task | Executed | Semantic pass | Mean model time |
|---|---:|---:|---:|---:|
| `sd15-smoke` | generation | 5/5 | 0/5 | 1.78 s |
| `qwen-image-benchmark` | generation | 5/5 | 4/5 | 38.19 s |
| `flux2-benchmark` | generation | 5/5 | 4/5 | 49.72 s |
| `qwen-edit-benchmark` | edit | 3/3 | 3/3 | 155.76 s |

## Preserved semantic failures

- `sd15-smoke/composition`: failed blue notebook. The notebook is white rather than blue; an unrequested red pencil is also present.
- `sd15-smoke/typography`: failed exact headline AI LAB 2026, exact line LOCAL MODELS, no extra text, legible typography. The poster contains malformed, unreadable pseudo-text instead of either requested line.
- `sd15-smoke/spatial`: failed three objects, cube in center, sphere on left, pyramid on right, requested colors. Only one yellow-green sphere is visible; the cube and pyramid are absent.
- `sd15-smoke/character-sheet`: failed green hat retained, four requested poses, no text. Four panels exist, but the hat is beige, requested running/reading actions are absent, and pseudo-text labels are visible.
- `sd15-smoke/romanian-scene`: failed morning fog. The cobblestone old-town scene and tower are present, but the requested light morning fog is absent.
- `qwen-image-benchmark/character-sheet`: failed no text. Identity, clothing and poses are consistent, but a visible numeral 2 appears in the running panel.
- `flux2-benchmark/character-sheet`: failed four panels, no text. The four poses are not enclosed in panels, and the book cover contains a visible text-like mark.

## OCR

The OCR fixtures are checksum-pinned. Character error rate (CER) is computed from
the API's canonical aggregate text; line-level text is used only when aggregate text
is absent. This avoids counting the same recognition twice.

| Profile | Executed | Exact | Mean CER | Mean confidence | Mean time |
|---|---:|---:|---:|---:|---:|
| `ocr-smoke` | 4/4 | 2/4 | 0.0219 | 0.9777 | 0.469 s |
| `ocr-server` | 4/4 | 3/4 | 0.0250 | 0.9815 | 0.502 s |

## Method and artifacts

- Prompts and rubrics: `harness/images/cases.json`.
- Image orchestration: `harness/images/run_images.py`, using only the public AI-Lab API.
- OCR orchestration and scoring: `harness/images/run_ocr.py`.
- Semantic evidence: `results/images/semantic-review.json` and `results/images/summary.json`.
- Generated library: `results/images/library/`.
- OCR fixtures and raw responses: `results/images/ocr/`.

Infrastructure and workflow incidents are excluded from model success rates. No such
incident is counted as a model failure in this pass.
