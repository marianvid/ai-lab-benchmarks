"""The media runners' bookkeeping, without a model: what they record and how."""

import struct
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from harness.audio import run_asr, run_vad
from harness.images import run_images
from harness.shared.textmetrics import ErrorTotals
from harness.video import run_echomimic_v3, run_ta2_local


class ImageRunTests(unittest.TestCase):
    def test_png_facts_read_the_size_from_the_header(self):
        header = run_images.PNG_SIGNATURE + b"\0\0\0\rIHDR" + struct.pack(">II", 640, 480)
        facts = run_images.png_facts(header)
        self.assertEqual((facts["png"], facts["width"], facts["height"]), (True, 640, 480))
        self.assertFalse(run_images.png_facts(b"GIF89a")["png"])

    def test_a_profile_that_will_not_load_runs_no_case(self):
        folder = Path(tempfile.mkdtemp())
        run = run_images.ProfileRun("http://manager", folder, folder / "summary.json",
                                    {"profiles": {}})
        with mock.patch.object(run_images, "unload_running", return_value=[]), \
                mock.patch.object(run_images, "load", return_value={"ok": False}), \
                mock.patch.object(run_images, "run_case") as run_case, \
                mock.patch("builtins.print"):
            run.profile("sd15", "sd15-smoke", "generate", [{"id": "c1"}])
        run_case.assert_not_called()
        self.assertTrue((folder / "summary.json").exists())


class AudioRunTests(unittest.TestCase):
    def test_asr_scores_and_an_empty_ratio(self):
        totals = ErrorTotals()
        totals.add("un doi trei", "un doi")
        figures = run_asr.scores([{"ok": True}, {"ok": False}], 2.0, totals, 10.0)
        self.assertEqual((figures["successful"], figures["failed"]), (1, 1))
        self.assertEqual((figures["real_time_factor"], figures["audio_seconds_per_second"]),
                         (0.2, 5.0))
        self.assertIsNone(run_asr.ratio(1, 0, 2))

    def test_vad_speed_counts_only_successful_requests(self):
        figures = run_vad.summary([{"ok": True, "inference_s": 1.0},
                                   {"ok": False, "inference_s": 9.0}], 4.0)
        self.assertEqual((figures["successful"], figures["inference_s"],
                          figures["audio_seconds_per_second"]), (1, 1.0, 4.0))


class VideoRunTests(unittest.TestCase):
    def arguments(self):
        return types.SimpleNamespace(case="host", steps=8, size=512, seed=43,
                                     max_vram_fraction=0.5, model_root="/models",
                                     fixtures="/fixtures")

    def test_the_benchmark_settings_are_laid_over_upstream(self):
        class Upstream:
            def __init__(self):
                self.guidance = 4.5
        implementation = types.SimpleNamespace(Config=Upstream)
        config = run_echomimic_v3.benchmark_config(implementation, self.arguments(), Path("/out"))()
        self.assertEqual((config.guidance, config.sample_size, config.test_name_list),
                         (4.5, [512, 512], ["host"]))
        self.assertEqual(config.wav2vec_model_dir, "/models/wav2vec2-base-960h")

    def test_the_memory_profile_is_applied_once(self):
        torch = types.SimpleNamespace(cuda=types.SimpleNamespace(
            get_device_properties=lambda _: types.SimpleNamespace(total_memory=2 * 1048576)))
        offload = mock.Mock()
        move = run_echomimic_v3.profiling_once(torch, offload, mock.Mock(), 0.5)
        pipeline = object()
        self.assertIs(move(pipeline), pipeline)
        move(pipeline)
        offload.profile.assert_called_once()
        self.assertEqual(offload.profile.call_args.kwargs["budgets"], {"*": 1})

    def test_the_record_names_the_newest_artifact(self):
        out = Path(tempfile.mkdtemp())
        (out / "host_audio.mp4").write_bytes(b"")
        torch = types.SimpleNamespace(cuda=types.SimpleNamespace(
            max_memory_allocated=lambda: 1, max_memory_reserved=lambda: 2))
        record = run_echomimic_v3.record_of(self.arguments(), torch, out, {
            "status": "succeeded", "error": None, "wall_s": 1.23456})
        self.assertEqual((record["wall_s"], record["artifact"]),
                         (1.235, str(out / "host_audio.mp4")))

    def test_paths_are_made_absolute(self):
        self.assertTrue(run_ta2_local.path("~/x").is_absolute())
