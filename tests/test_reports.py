"""The published pages are what the report generators make from the committed results."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import make_report
from harness.audio import make_report as audio_report
from harness.images import apply_reviews
from harness.images import make_report as images_report
from harness.textreport import extras, loading, quality, speed
from harness.textreport.table import cell, header, ladder
from harness.textreport.table import tested as models_tested

ROOT = Path(__file__).resolve().parents[1]


class TableTests(unittest.TestCase):
    def test_headers_link_their_definition_and_cells_format(self):
        self.assertTrue(header("TTFT", "s").startswith("[TTFT](glossary.md#ttft"))
        self.assertTrue(header("TTFT", "s").endswith(" (s)"))
        self.assertEqual(header("Model"), "Model")
        self.assertEqual((cell(None), cell(1.23456, 2), cell(3)), ("—", "1.23", "3"))

    def test_ladder_and_tested(self):
        entry = {"curve": {"1": {"items_per_s": 2.0}, "64": {"items_per_s": 10.0}}}
        self.assertEqual(ladder(entry, "curve")[1], "5.0×")
        summary = {"a": {"tested": True, "load": {"ok": True}, "model": "B", "engine": "x"},
                   "b": {"tested": True, "load": {"ok": False}, "model": "A", "engine": "y"}}
        self.assertEqual([row["model"] for row in models_tested(summary)], ["B"])


class PublishedPagesTests(unittest.TestCase):
    def test_the_text_pages_are_regenerated_unchanged(self):
        out = Path(tempfile.mkdtemp())
        argv = ["make_report.py", "--results", str(ROOT / "results"), "--out", str(out)]
        with mock.patch("sys.argv", argv), mock.patch("builtins.print"):
            self.assertEqual(make_report.main(), 0)
        for page in sorted(out.glob("*.md")):
            with self.subTest(page=page.name):
                self.assertEqual(page.read_text(), (ROOT / "docs" / page.name).read_text())

    def test_the_audio_page_is_regenerated_unchanged(self):
        out = Path(tempfile.mkdtemp()) / "audio-results.md"
        argv = ["make_report.py", "--results", str(ROOT / "results" / "audio"), "--out", str(out)]
        with mock.patch("sys.argv", argv):
            self.assertEqual(audio_report.main(), 0)
        self.assertEqual(out.read_text(), (ROOT / "docs" / "audio-results.md").read_text())


class PageSectionTests(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())

    def test_pages_without_measurements_say_so(self):
        with mock.patch("builtins.print"):
            speed.latency_page([], self.out)
            speed.throughput_page([], self.out)
        self.assertIn("Not yet measured in this run.", (self.out / "latency.md").read_text())
        self.assertIn("## Long prompts — whole articles\n\nNot yet measured",
                      (self.out / "throughput.md").read_text())

    def test_missing_results_leave_their_pages_unwritten(self):
        extras.tokenizer_page(self.out, self.out)
        extras.agentic_page(self.out, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_a_model_without_a_task_gets_dashes(self):
        rows = [{"model": "M", "engine": "E"}]
        self.assertEqual(quality.classification_table(rows)[-1], "| M | E | — | — | — | — | — |")
        self.assertEqual(quality.translation_table(rows)[-1], "| M | E | — | — | — |")
        self.assertEqual(loading.seconds(None), "—")


class ImagePagesTests(unittest.TestCase):
    def test_the_image_page_is_regenerated_unchanged(self):
        out = Path(tempfile.mkdtemp()) / "images-ocr.md"
        argv = ["make_report.py", "--linux-images", str(ROOT / "results/images/summary.json"),
                "--mac-images", str(ROOT / "results/images/macos/summary.json"),
                "--linux-ocr", str(ROOT / "results/images/ocr/results.json"),
                "--mac-ocr", str(ROOT / "results/images/macos/ocr/results.json"),
                "--cases", str(ROOT / "harness/images/cases.json"), "--out", str(out)]
        with mock.patch("sys.argv", argv):
            self.assertEqual(images_report.main(), 0)
        self.assertEqual(out.read_text(), (ROOT / "docs" / "images-ocr.md").read_text())

    def test_applying_the_recorded_reviews_again_changes_nothing(self):
        summary = Path(tempfile.mkdtemp()) / "summary.json"
        shutil.copy(ROOT / "results/images/summary.json", summary)
        argv = ["apply_reviews.py", "--summary", str(summary),
                "--reviews", str(ROOT / "results/images/semantic-review.json")]
        with mock.patch("sys.argv", argv):
            self.assertEqual(apply_reviews.main(), 0)
        self.assertEqual(summary.read_text(), (ROOT / "results/images/summary.json").read_text())

    def test_a_drifted_rubric_is_refused(self):
        case = {"rubric": ["a", "b"]}
        review = {"criteria": {"b": True, "a": True}, "notes": ""}
        with self.assertRaisesRegex(RuntimeError, "rubric drift"):
            apply_reviews.reviewed(case, review, {"reviewer": "r", "reviewed_at": "t"}, "p/c")
