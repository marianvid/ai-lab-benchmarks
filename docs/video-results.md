# Presenter video generation — results

These tests cover a narrow production task: animate a still host, guest or
character from an English speech track. They do not measure cinematic
text-to-video. See [the method](video-method.md) for inputs, settings and metric
definitions.

> **How to read this page:** every verdict below is automatic. A successful
> file, strong identity score or SyncNet result does not decide whether a
> performance looks natural. The [video output page](video-listening.html)
> places source portraits beside the publishable generated clips and assigns
> no viewing score. The audio tracks are separately produced inputs; their
> casting is not included in the automatic video verdict. Licence-restricted
> media is not published.

## Feasibility and resource cost

| Model and case | Result | Output | Wall time | Peak GPU | Peak process RAM | Automatic verdict |
|---|---|---:|---:|---:|---:|---|
| EchoMimicV3 · documentary host | Success | 2.92 s, 512×512, 25 fps | 2 min 16 s | 11.2 GiB allocated | Not recorded by the first runner | **Viable with reservations:** fast enough for short inserts; identity drift is measurable |
| EchoMimicV3 · roundtable guest | Success | 5.84 s, 512×512, 25 fps | 2 min 46 s | 13.4 GiB allocated | Not recorded by the first runner | **Viable with reservations:** more motion than LatentSync, but weaker identity retention |
| EchoMimicV3 · animated storyteller | Failed before generation | — | 1 min 33 s | 0.35 GiB allocated | Not recorded | **Not compatible with this character:** the upstream face detector rejected the non-human fox portrait |
| LatentSync 1.6 · documentary host | Success | 6.08 s, 768×768, 25 fps | 5 min 0 s | 16.6 GiB observed | 10.7 GiB observed | **Viable for a locked presenter tile:** very stable face and strong identity retention |
| MuseTalk 1.5 · documentary host | Success | 6.00 s, 768×768, 25 fps | 1 min 0 s | 7.2 GiB observed | 4.5 GiB observed | **Fast, but needs correction:** low resource cost and complete duration, with measurable identity change and AV offset |
| InfiniteTalk 14B FP8 · documentary host | Success with duration mismatch | 3.24 s, 640×640, 25 fps | 2 h 6 min | 15.3 GiB observed | 33.6 GiB observed | **Not production-efficient here:** expressive output and strong SyncNet confidence, but an 80 ms offset and only 3.24 s were saved from the requested 81-frame run |
| JoyVASA animal · animated storyteller | Success | 6.12 s, 512×512, 25 fps | 40 s | 18.7 GiB observed | 4.0 GiB observed | **Compatible non-human path:** the dedicated animal pipeline completed the fox animation; human face and SyncNet scores do not apply |
| LivePortrait Animals · animated storyteller | Success | 3.12 s, 512×512, 25 fps | 18 s | 3.8 GiB observed | 4.2 GiB observed | **Fast controlled motion transfer:** the fox followed a 78-frame driving video; human face and speech-sync metrics do not apply |
| Wan2.2-S2V 14B FP8 scaled · animated storyteller | Success | 4.81 s, 640×640, 16 fps | 8 min 9 s | Peak not captured; 14.8 GiB remained resident after completion | Peak not captured; 25.8 GiB RSS remained after completion | **Feasible with native offload:** all 77 requested frames and audio were saved; human-face and SyncNet metrics do not apply |
| LongCat-Video-Avatar 1.5 INT8 · documentary host | Success | 3.00 s, 640×608, 25 fps | 4 min 29 s | 24.2 GiB observed | 21.9 GiB observed | **Viable but offset:** best new-candidate identity score and strong mouth/audio correspondence, with an 80 ms detected offset |
| LongCat-Video-Avatar 1.5 INT8 · roundtable guest | Success | 6.00 s, 640×608, 25 fps | 7 min 17 s | 28.6 GiB observed | 22.0 GiB observed | **Viable with reservations:** expressive six-second output, but lower identity minimum and an 80 ms offset |
| LongCat-Video-Avatar 1.5 INT8 · animated storyteller | Success | 6.00 s, 640×608, 25 fps | 7 min 30 s | 28.6 GiB observed | 22.0 GiB observed | **Useful character route:** accepted the non-human portrait and produced all requested media; human-face metrics do not apply |
| TA2.0 · documentary host | Success | 8.96 s, 640×608, 25 fps | 7 min 55 s | 28.0 GiB observed | 26.5 GiB observed | **Strong final presenter result:** zero detected AV offset, stable identity and complete output |
| TA2.0 · roundtable guest | Success | 14.08 s, 640×608, 25 fps | 12 min 52 s | 28.0 GiB observed | 26.1 GiB observed | **Strong final guest result:** zero offset, strong confidence and the best identity retention in the new guest set |
| TA2.0 · animated storyteller | Success | 6.00 s, 640×608, 25 fps | 5 min 49 s | 28.0 GiB observed | 26.0 GiB observed | **Useful character route:** completed the non-human case; human-face and SyncNet metrics do not apply |
| SkyReels V3 Talking Avatar 19B FP8 · documentary host | Failed during model construction | — | 2 min 43 s in the 64 GiB boundary attempt | 5.4 GiB observed before termination | 62.9 GiB observed | **Not viable in this configuration:** official low-VRAM/offload mode exhausted 64 GiB RAM plus 8 GiB swap before generation |

The successful human-portrait runs fit inside 32 GB of VRAM, but LongCat and
TA2.0 use most of the card and should not be described as comfortable fits. At
these settings MuseTalk needed roughly 10 seconds per output second,
EchoMimic 28–47 seconds and LatentSync roughly 49 seconds. InfiniteTalk needed
about 39 minutes per saved output second. These ratios include model start-up
and output encoding and should not be treated as steady-state throughput.
The native Wan2.2 run needed about 102 seconds per output second. Its corrective
run was started directly through ComfyUI rather than through the polling
wrapper, so resident post-run values are retained as lower bounds and are not
mislabelled as peak measurements.
LongCat needed about 73–90 seconds per output second; the final TA2.0 runs
needed about 53–58 seconds per output second.
SkyReels did not reach inference even after the system-memory boundary was
raised from 48 to 64 GiB.

## Face and temporal measurements

Every fifth frame is compared with the source portrait. Higher identity cosine
is better. Frame delta measures average normalized pixel change between sampled
frames; lower is more stable but can also mean a less expressive result.

| Model and case | Face found | Identity mean | Identity minimum | Face-area variation | Frame delta | Automatic reading |
|---|---:|---:|---:|---:|---:|---|
| LatentSync · documentary host | 100% | **0.954** | **0.939** | **0.22%** | **0.00123** | Strongest identity and geometry stability; movement is restrained |
| EchoMimicV3 · documentary host | 100% | 0.890 | 0.769 | 0.70% | 0.00605 | More visible motion, with occasional identity deviation |
| EchoMimicV3 · roundtable guest | 100% | 0.856 | 0.669 | 1.12% | 0.00543 | Stable detection but the weakest minimum identity score in this pass |
| InfiniteTalk 14B FP8 · documentary host | 100% | 0.809 | 0.698 | 1.83% | 0.01748 | Most visible generated facial motion, with substantial identity and geometry variation |
| MuseTalk 1.5 · documentary host | 100% | 0.732 | 0.706 | 0.38% | 0.00130 | Geometry remains locked, but the face embedding changes substantially around the generated mouth |
| LongCat-Video-Avatar 1.5 INT8 · documentary host | 100% | **0.818** | **0.674** | 2.87% | 0.00600 | Best identity retention among the two new candidates; visibly broader expression increases geometry change |
| TA2.0 · documentary host | 100% | 0.814 | **0.689** | **1.71%** | 0.01277 | Similar mean identity to LongCat, with a stronger minimum and more temporal change across the longer performance |
| LongCat-Video-Avatar 1.5 INT8 · roundtable guest | 100% | **0.750** | **0.533** | 3.48% | 0.01126 | More expression and temporal change, with a weak minimum identity frame |
| TA2.0 · roundtable guest | 100% | **0.830** | **0.720** | **1.27%** | 0.01010 | Best identity retention and geometric stability in the new guest set |

The automatic comparison favours LatentSync when a composited meeting tile
must remain visually consistent. EchoMimic is the more animated route, but its
extra motion comes with a measurable cost in identity stability. This is a
trade-off, not a universal ranking. In the final 640×608 set, TA2.0 improves
substantially over its preliminary portrait-shaped runs and leads the guest
comparison; the host result is close to LongCat in mean identity and stronger
at its weakest sampled frame. Neither matches LatentSync's source-identity
score because both synthesize the full performance rather than editing only
the mouth region.

## Audio-video synchronization

The official LatentSync SyncNet evaluator processed all successful human-
presenter clips reported in the table. Confidence is meaningful only within this evaluator and set;
a value near another model's value is not a calibrated percentage. Offset is
measured in 25 fps video frames, so four frames are 160 ms.

| Model and case | SyncNet confidence | AV offset | Automatic verdict |
|---|---:|---:|---|
| LatentSync · documentary host | **5.19** | **0 frames** | **Pass:** strongest confidence and no detected timing offset |
| EchoMimicV3 · documentary host | 3.05 | -4 frames | **Needs attention:** moderate confidence and 160 ms detected offset |
| EchoMimicV3 · roundtable guest | 1.40 | -3 frames | **Fail for direct use:** weak confidence and 120 ms detected offset |
| InfiniteTalk 14B FP8 · documentary host | **8.84** | -2 frames | **Needs attention:** strongest confidence, but an 80 ms timing correction is still required |
| MuseTalk 1.5 · documentary host | **7.85** | -3 frames | **Needs attention:** strong confidence, but a 120 ms timing correction is required |
| LongCat-Video-Avatar 1.5 INT8 · documentary host | **9.65** | -2 frames | **Needs attention:** very strong correspondence, but an 80 ms timing correction is required |
| LongCat-Video-Avatar 1.5 INT8 · roundtable guest | 5.05 | -2 frames | **Needs attention:** usable confidence, but the same 80 ms correction is required |
| TA2.0 · documentary host | **7.80** | **0 frames** | **Pass:** strong confidence and no detected timing offset |
| TA2.0 · roundtable guest | **7.95** | **0 frames** | **Pass:** strongest zero-offset result in the new candidate set |

LatentSync remains the automatic identity winner for a constrained lip-sync
edit. TA2.0 has zero offset in both final cases and combines this with stronger
full-frame generated performances. InfiniteTalk and MuseTalk produce strong
correspondence between mouth motion and audio, but the measured offsets still
require correction. EchoMimic's clips remain useful
evidence about generative movement, but should not be treated as ready speaker
tiles without correcting timing and checking the resulting mouth motion.
These synchronization results say nothing about whether the voice's perceived
gender, age, pitch, accent or persona matches the source portrait. Voice
selection and processing remain a separate production stage.

## Production implications

- A grid-style discussion programme is realistic if each participant is
  generated as a separate locked shot and assembled afterward. It does not
  require one model to generate the complete multi-person screen.
- LatentSync is the safer first choice for recurring photorealistic hosts whose
  portrait must remain recognisable.
- MuseTalk is the cheapest successful route in this pass, but its mouth-region
  identity change and 120 ms offset need correction before direct use.
- InfiniteTalk creates the richest facial performance in the contact sheet,
  but this FP8/offload configuration is too slow for routine production and its
  saved-frame rate shortened the requested clip.
- EchoMimic is useful where restrained head and facial motion matters more than
  exact identity, provided the source is a human face accepted by its detector.
- A polished non-human character needs a character-aware animation or rigging
  path. JoyVASA's animal mode accepted and animated the fox that EchoMimic's
  human face detector rejected. The English performance remains available for
  direct inspection; it is not assigned a human-face or SyncNet score.
- LivePortrait Animals was the fastest controlled character route in this
  pass. Its 3.12-second driving clip completed in 17.5 seconds including model
  loading. The driver provides the performance rather than asking the model to
  invent motion from audio. The contact sheet also exposes the trade-off:
  transferred mouth shapes can introduce human-like teeth on a stylised animal.
- Wan2.2-S2V completed all 77 requested frames in 8 minutes 9 seconds through
  the checkpoint's native ComfyUI loader. It remains an offline renderer. A
  preliminary DiffSynth adapter produced corrupted frames; only the native
  result is included on the viewing page and the failed adapter is documented
  in the method rather than treated as model failure.
- LongCat is the stronger new choice when facial identity and expressive motion
  matter most. It also accepted the animated fox, but both human clips need an
  80 ms timing correction and the two-segment runs approach 29 GiB VRAM.
- TA2.0 is the stronger new choice when zero-offset synchronization and a
  complete generated performance matter. The final 640×608 host and guest
  clips also improve its identity results substantially. It requires sequential
  UMT5/video offload to fit.
- SkyReels V3 Talking Avatar 19B is outside this machine's practical memory
  envelope in the official low-VRAM path. Failure before generation at the
  64 GiB RAM boundary is the result; no quality claim is made.
- Rendering remains offline production: these runs are tens of times slower
  than real time, but short reusable shots and speaker tiles are practical.

## Raw material

Machine-readable run records, publishable generated clips and automatic face
measurements are under [`results/video`](../results/video/). The reproducible
runners, fixtures and redistributable compatibility patches are under
[`harness/video`](../harness/video/).
