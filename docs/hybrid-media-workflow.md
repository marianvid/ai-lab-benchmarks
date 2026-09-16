# Hybrid media production workflow

The practical production system separates controlled local generation from
the final editorial assembly. No single video model is expected to create a
complete programme continuously.

## Local RTX stage

The RTX system prepares still characters, English speech, reusable idle loops,
driven facial performances and lip-synchronised speaker tiles. A discussion is
rendered one participant at a time. This keeps identities stable and allows a
failed shot to be regenerated without rebuilding the complete programme.

LivePortrait-style driving clips are especially efficient: the driver supplies
the acting, gaze and head movement, while the local model transfers that
performance to the selected character. MuseTalk or LatentSync can then correct
the mouth for the final speech track when needed.

## Optional commercial stage

An online service can supply short neutral driving clips or difficult cinematic
inserts when local generation is not competitive. The purchased output should
be treated as source footage rather than the editorial product. Sensitive
scripts, final narration and the assembled argument can remain local; only the
minimum neutral motion request needs to leave the system.

## Mac finishing stage

Final Cut Pro assembles speaker tiles, cuts, overlays, captions, still imagery
and generated inserts. Logic Pro handles dialogue cleanup, room tone, music,
effects, loudness and the audio master. These applications remain manually
controlled; the benchmark records the intended hand-off but does not operate
or modify either application.

This design makes a repeatable programme realistic on the available hardware:
local models produce controlled components, optional services fill narrow
quality gaps, and the Mac turns those components into the publishable edition.
