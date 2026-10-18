"""What every local generation run records."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.shared import runs
from harness.shared.speech_eval import generated, spread


class RunsTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def test_cases_record_success_and_failure_and_go_on(self):
        def generate(index, case):
            if case["id"] == "bad":
                raise RuntimeError("out of memory")
            return {"seconds": index}
        records = runs.run_cases([{"id": "good"}, {"id": "bad"}],
                                 lambda _index, case: {"id": case["id"]}, generate, trace=True)
        self.assertEqual(records[0], {"id": "good", "ok": True, "seconds": 0})
        self.assertEqual(records[1]["error"], "RuntimeError: out of memory")
        self.assertIn("Traceback", records[1]["traceback"])

    def test_raw_json_and_the_exit_code(self):
        self.assertEqual(runs.write_raw(self.folder, {"cases": [{"ok": True}]}), 0)
        self.assertEqual(runs.write_raw(self.folder, {"cases": [{"ok": False}]}), 1)
        self.assertEqual(json.loads((self.folder / "raw.json").read_text())["cases"], [{"ok": False}])

    def test_folders_manifests_checksums_and_arguments(self):
        out, audio = runs.output_folder(str(self.folder / "run"))
        self.assertTrue(audio.is_dir() and audio.parent == out)
        manifest = self.folder / "manifest.json"
        manifest.write_text(json.dumps({"cases": [{"id": 1}, {"id": 2}, {"id": 3}]}))
        self.assertEqual(runs.manifest_cases(manifest, 2), [{"id": 1}, {"id": 2}])
        self.assertEqual(len(runs.manifest_cases(manifest)), 3)
        self.assertEqual(len(runs.sha256(manifest)), 64)
        args = runs.runner_arguments(reference=True).parse_args(
            ["--model", "m", "--manifest", "x", "--reference-audio", "a",
             "--reference-text", "t", "--out", "o"])
        self.assertEqual((args.model, args.reference_text), ("m", "t"))

    def test_successful_cases_and_their_spread(self):
        (self.folder / "raw.json").write_text(json.dumps(
            {"cases": [{"id": "a", "ok": True}, {"id": "b", "ok": False}]}))
        found = list(generated(self.folder))
        self.assertEqual([(case["id"], path.name) for case, path in found], [("a", "a.wav")])
        self.assertEqual(spread([1.0, 2.0, 4.0]), {"mean": 2.333333, "min": 1.0, "max": 4.0})


class FakeRunner(runs.Runner):
    """A runner whose model is a function: nothing loads, nothing touches a card."""

    reference = True

    def options(self, parser):
        parser.add_argument("--limit", type=int)

    def load_timed(self):
        self.load_s = 1.5

    def generate(self, index, case):
        if case["id"] == "broken":
            raise ValueError("cannot say it")
        self.destination(case).write_bytes(b"audio")
        return {"index": index}

    def facts(self, records):
        return {"engine": "fake", "load_s": self.load_s, "reference": self.args.reference_text}


class RunnerTests(unittest.TestCase):
    def test_a_run_writes_every_case_and_says_whether_all_succeeded(self):
        folder = Path(tempfile.mkdtemp())
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps({"cases": [
            {"id": "one", "language": "en", "text": "a"},
            {"id": "broken", "language": "en", "text": "b"},
            {"id": "three", "language": "en", "text": "c"}]}))
        argv = ["--model", "m", "--manifest", str(manifest), "--reference-audio", "r.wav",
                "--reference-text", "hello", "--out", str(folder / "run"), "--limit", "2"]
        runner = FakeRunner()
        self.assertEqual(runner.main(argv), 1)
        raw = json.loads((folder / "run" / "raw.json").read_text())
        self.assertEqual((raw["engine"], raw["load_s"], raw["reference"]), ("fake", 1.5, "hello"))
        self.assertEqual([case["id"] for case in raw["cases"]], ["one", "broken"])
        self.assertEqual(raw["cases"][1]["error"], "ValueError: cannot say it")
        self.assertTrue((folder / "run" / "audio" / "one.wav").exists())
        self.assertEqual(runner.model_path.name, "m")
        self.assertEqual(runs.peak_of([{"peak_vram_bytes": 3}, {}]), 3)
