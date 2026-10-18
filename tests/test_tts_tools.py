"""The TTS tools that need no model: preparing the set, blinding it, checking and reporting it."""

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from harness.tts import make_libritts_baseline, make_listening_pack, make_report, prepare_libritts
from harness.tts.scoring import score_asr, validate_results


class PrepareTests(unittest.TestCase):
    def test_items_are_spread_evenly_with_both_ends(self):
        self.assertEqual(prepare_libritts.evenly(list(range(10)), 3), [0, 4, 9])
        self.assertEqual(prepare_libritts.evenly([1, 2, 3], 1), [2])
        with self.assertRaises(ValueError):
            prepare_libritts.evenly([1], 2)

    def test_a_clip_fits_by_length_and_words(self):
        clip = prepare_libritts.Clip(Path("a.wav"), "one two three", 3.0)
        self.assertTrue(clip.fits((2.5, 12.0), (2, 45)))
        self.assertFalse(clip.fits((2.5, 12.0), (6, 45)))

    def test_a_wav_duration(self):
        path = Path(tempfile.mkdtemp()) / "a.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            handle.writeframes(b"\0\0" * 4000)
        self.assertEqual(prepare_libritts.duration(path), 0.5)


class BaselineTests(unittest.TestCase):
    def test_the_human_recordings_become_a_run(self):
        data, out = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (data / "target.wav").write_bytes(b"RIFF")
        (data / "manifest.json").write_text(json.dumps({"cases": [
            {"id": "c1", "target_audio": "target.wav", "target_duration_s": 2.0,
             "target_sha256": "abc"}]}))
        with mock.patch("sys.argv", ["x", "--data", str(data), "--out", str(out)]):
            self.assertEqual(make_libritts_baseline.main(), 0)
        case = json.loads((out / "raw.json").read_text())["cases"][0]
        self.assertEqual((case["ok"], case["sha256"], case["audio_duration_s"]), (True, "abc", 2.0))
        self.assertTrue((out / "audio" / "c1.wav").is_symlink())


class ListeningPackTests(unittest.TestCase):
    def test_each_case_has_its_own_fixed_order(self):
        order = make_listening_pack.shuffled("speaker-02")
        self.assertEqual(order, make_listening_pack.shuffled("speaker-02"))
        self.assertEqual(sorted(order), sorted(make_listening_pack.MODELS))

    def test_a_blind_case_hides_which_model_is_which(self):
        results, out = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        for label, folder in make_listening_pack.MODELS.items():
            (results / folder / "audio").mkdir(parents=True)
            (results / folder / "audio" / "s-02.wav").write_bytes(label.encode())
        (out / "audio").mkdir()
        candidates, mapping = make_listening_pack.blind_case({"id": "s-02"}, results, out)
        self.assertEqual([c["slot"] for c in candidates], ["A", "B", "C", "D", "E", "F"])
        for slot, label in mapping.items():
            self.assertEqual((out / "audio" / "s-02" / f"{slot}.wav").read_bytes(), label.encode())


class ValidationTests(unittest.TestCase):
    def test_a_short_manifest_is_refused(self):
        with self.assertRaisesRegex(validate_results.ResultsError, "cases"):
            validate_results.check_manifest({"cases": [{"id": "a"}], "speakers": []})

    def test_a_balanced_manifest_passes(self):
        cases = [{"id": str(n)} for n in range(validate_results.CASES)]
        speakers = [{"gender": "F"}] * 5 + [{"gender": "M"}] * 5
        self.assertEqual(len(validate_results.check_manifest(
            {"cases": cases, "speakers": speakers})), validate_results.CASES)


class AsrGroupTests(unittest.TestCase):
    def test_rates_per_gender_count_only_scored_cases(self):
        records: list[dict] = [{"gender": "F", "word_errors": 1, "reference_words": 4,
                    "character_errors": 2, "reference_characters": 20},
                   {"gender": "F"}]
        self.assertEqual(score_asr.groups(records),
                         {"by_gender": {"F": {"wer": 0.25, "cer": 0.1, "completed": 1}}})


class TtsReportTests(unittest.TestCase):
    def test_wer_and_rtf_are_ratios_of_sums_and_intervals_repeat(self):
        rows = [{"speaker": "a", "word_errors": 1, "reference_words": 10, "seconds": 1,
                 "audio_duration_s": 2},
                {"speaker": "b", "word_errors": 3, "reference_words": 10, "seconds": 3,
                 "audio_duration_s": 2}]
        self.assertEqual(make_report.statistic(rows, "wer"), 0.2)
        self.assertEqual(make_report.statistic(rows, "rtf"), 1.0)
        first = make_report.bootstrap(rows, "wer")
        assert first is not None
        self.assertEqual(first, make_report.bootstrap(rows, "wer"))
        self.assertLessEqual(first[0], first[1])
        self.assertIsNone(make_report.bootstrap([], "wer"))

    def test_rows_show_dashes_for_what_is_missing(self):
        model = {"label": "M", "completed": 99, "wer": 0.1, "utmos": None,
                 "speaker_similarity_to_target": 0.5, "rtf": None, "duration_ratio": 1.0,
                 "peak_vram_bytes": 2e9, "wer_ci95": [0.1, 0.2], "utmos_ci95": None,
                 "speaker_similarity_ci95": None, "rtf_ci95": None}
        self.assertEqual(make_report.score_row(model),
                         "| M | 99/100 | 0.100 | — | 0.500 | 1.000 | — | 2.0 GB |")
        self.assertEqual(make_report.interval_row(model), "| M | 0.100–0.200 | — | — | — |")
