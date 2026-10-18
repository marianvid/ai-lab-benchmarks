"""The scripts that need an engine's own libraries: each is imported and its
pure parts checked where those libraries are installed, and skipped where they are not.

The skip names the missing library, so a run on a machine without it says
what it did not check rather than passing quietly.
"""

import argparse
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


def have(*libraries: str) -> bool:
    """Whether every library is installed here."""
    return all(importlib.util.find_spec(name) is not None for name in libraries)


def needs(*libraries: str):
    """Skip the test unless every library is installed."""
    return unittest.skipUnless(have(*libraries), "needs " + ", ".join(libraries))


def command_line(runner) -> argparse.Namespace:
    """The runner's command line, parsed with only its required options given."""
    from harness.shared.runs import runner_arguments
    parser = runner_arguments(model=runner.takes_model, manifest=runner.takes_manifest,
                              reference=runner.reference)
    runner.options(parser)
    argv: list[str] = []
    for action in parser._actions:
        if action.required and action.option_strings:
            argv += [action.option_strings[0],
                     str(next(iter(action.choices))) if action.choices else "x"]
    return parser.parse_args(argv)


TTS = ("torch", "soundfile", "psutil")


class TtsRunnerTests(unittest.TestCase):
    @needs(*TTS, "qwen_tts")
    def test_qwen_clone(self):
        from harness.tts.runners import run_qwen
        self.assertEqual(command_line(run_qwen.QwenClone()).reference_text, "x")
        self.assertIsNone(run_qwen.revision(Path(tempfile.mkdtemp())))

    @needs(*TTS, "qwen_tts")
    def test_qwen_controlled_makes_one_file_per_speaker(self):
        from harness.tts.runners import run_qwen_controlled
        case = {"id": "c", "category": "k", "text": "t", "voice_design": "calm",
                "custom_instruction": "warm", "custom_speakers": ["Ana", "Bob"]}
        self.assertEqual([v["id"] for v in run_qwen_controlled.variants([case], "custom-voice")],
                         ["c--ana", "c--bob"])
        self.assertEqual(run_qwen_controlled.variants([case], run_qwen_controlled.DESIGN)[0]
                         ["instruction"], "calm")
        command_line(run_qwen_controlled.QwenControlled())

    @needs(*TTS, "omnivoice")
    def test_omnivoice_runs(self):
        from harness.tts.runners import omnivoice_runner, run_omnivoice, run_omnivoice_design
        self.assertTrue(issubclass(run_omnivoice.OmniVoiceClone, omnivoice_runner.OmniVoiceRunner))
        self.assertEqual(command_line(run_omnivoice.OmniVoiceClone()).steps, 32)
        design = run_omnivoice_design.OmniVoiceDesign()
        self.assertFalse(hasattr(command_line(design), "manifest"))
        self.assertEqual(len(design.cases()), 3)

    @needs(*TTS, "torchaudio", "fireredtts3")
    def test_firered_runs(self):
        from harness.tts.runners import firered, run_firered_base, run_firered_instruct
        self.assertEqual(firered.language_of({"language": "ro"}), "Romanian")
        command_line(run_firered_base.FireRedBase())
        command_line(run_firered_instruct.FireRedInstruct())

    @needs(*TTS, "chatterbox")
    def test_chatterbox_takes_no_model_path(self):
        from harness.tts.runners import run_chatterbox_turbo
        self.assertFalse(hasattr(command_line(run_chatterbox_turbo.ChatterboxTurbo()), "model"))

    @needs("torch", "dia2")
    def test_dia2(self):
        from harness.tts.runners import run_dia2
        command_line(run_dia2.Dia2Dialogue())

    @needs(*TTS, "transformers")
    def test_mms(self):
        from harness.tts.runners import run_mms
        command_line(run_mms.MmsRomanian())

    @needs("ormsgpack", "requests", "fish_speech")
    def test_fish_clone(self):
        from harness.tts.runners import run_fish
        self.assertTrue(command_line(run_fish.FishClone()).reference_audio)

    @needs("soundfile", "psutil")
    def test_libritts_picks_the_engine_named(self):
        from harness.tts.runners import run_libritts
        args = command_line(run_libritts.LibriTTSRun())
        self.assertIsInstance(run_libritts.engine_for(args, Path("m")), run_libritts.Engine)


class SoundEffectTests(unittest.TestCase):
    @needs("soundfile", "torch", "stable_audio_3")
    def test_stable_audio3(self):
        from harness.soundfx import run_stable_audio3
        command_line(run_stable_audio3.StableAudio3())

    @needs("soundfile", "torch", "tangoflux")
    def test_tangoflux(self):
        from harness.soundfx import run_tangoflux
        command_line(run_tangoflux.TangoFlux())

    @needs("librosa", "torch", "transformers")
    def test_score_clap(self):
        from harness.soundfx import score_clap
        self.assertTrue(callable(score_clap.Clap.similarity))


class ScoringTests(unittest.TestCase):
    @needs("torch")
    def test_utmos_groups(self):
        from harness.tts.scoring import score_utmos
        cases = [{"mode": "clone", "mos": 3.0, "gender": "F"},
                 {"mode": "clone", "mos": 4.0, "gender": "M"}]
        result = score_utmos.summary(cases)
        self.assertEqual((result["by_mode"], result["by_gender"]),
                         ({"clone": 3.5}, {"F": 3.0, "M": 4.0}))

    @needs("torch", "torchmetrics")
    def test_nisqa(self):
        from harness.tts.scoring import score_nisqa
        self.assertTrue(callable(score_nisqa.score))

    @needs("torch", "pyannote")
    def test_speaker_similarity(self):
        from harness.tts.scoring import score_libritts_similarity, score_speaker_similarity
        cases = [{"gender": "F", "m": 0.5}, {"gender": "F", "m": 1.0}, {"gender": "M", "m": 0.0}]
        self.assertEqual(score_libritts_similarity.average(cases, "m", "gender", "F"), 0.75)
        self.assertTrue(callable(score_speaker_similarity.main))


class AudioTests(unittest.TestCase):
    @needs("pyarrow")
    def test_fleurs_rows_are_spread_evenly(self):
        from harness.audio import prepare_fleurs
        self.assertEqual(prepare_fleurs.evenly_spaced(10, 3), [0, 3, 6])
        with self.assertRaises(ValueError):
            prepare_fleurs.evenly_spaced(3, 4)

    @needs("pyannote")
    def test_diarization_reads_the_speaker_count_from_the_name(self):
        from harness.audio import run_diarization
        self.assertEqual(run_diarization.speakers_in("meeting_3spk"), 3)
        with self.assertRaises(ValueError):
            run_diarization.speakers_in("meeting")

    @needs("mlx_whisper")
    def test_mlx_whisper(self):
        from harness.audio.macos import run_mlx_whisper
        self.assertTrue(callable(run_mlx_whisper.main))


class TextToolTests(unittest.TestCase):
    @needs("sacrebleu")
    def test_numbers_survive_group_separators(self):
        from harness import bench_translate
        self.assertEqual(bench_translate.numbers_in("4,475 and 4 475 and 12"),
                         ["4475", "4475", "12"])

    @needs("transformers")
    def test_tokens_are_counted_per_language(self):
        from harness import tokratio
        tokenizer = types.SimpleNamespace(encode=lambda line, add_special_tokens: line.split())
        with mock.patch("builtins.print"):
            rows = tokratio.count(tokenizer, {"en": ["a b", "c"]},
                                  {"en": ("eng", "English", "Latin")})
        self.assertEqual(rows["en"]["tokens"], 3)

    @needs("PIL")
    @unittest.skipUnless(sys.version_info >= (3, 11), "needs Python 3.11 (datetime.UTC)")
    def test_ocr_prefers_the_aggregate_text(self):
        from harness.images import run_ocr
        self.assertEqual(run_ocr.normalize(" a\n b "), "A B")
        self.assertEqual(run_ocr.model_score([{"exact_match": True, "cer": 0.0,
                                               "mean_confidence": None}])["exact_matches"], 1)


class VideoTests(unittest.TestCase):
    @needs("cv2", "numpy", "insightface")
    def test_cosine_of_zero_is_zero(self):
        import numpy as np

        from harness.video import evaluate_video
        self.assertEqual(evaluate_video.cosine(np.zeros(2), np.ones(2)), 0.0)
        self.assertIsNone(evaluate_video.mean_or_none([]))

    @needs("psutil")
    def test_measured_runs_sample_the_process_tree(self):
        import psutil

        from harness.video import run_measured
        self.assertGreater(run_measured.rss_tree(psutil.Process()), 0)
        self.assertEqual(len(run_measured.gpu_sample()), 2)
        monitor = run_measured.Monitor.__new__(run_measured.Monitor)
        monitor.samples = [{"rss_bytes": 1}, {"rss_bytes": 3}]
        self.assertEqual(monitor.peak("rss_bytes"), 3)
