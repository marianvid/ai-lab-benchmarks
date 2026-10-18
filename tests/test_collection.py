"""Collecting the data and running the night: what is kept, what is recorded."""

import argparse
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from harness import fetch_wikipedia, get_datasets, measure_oversize, run_all

PROSE = "\n".join(["word " * 30] * 3)
MODEL = run_all.Model("text-bulk", 1, "Gemma", "vLLM", "NVFP4", True)


class WikipediaTests(unittest.TestCase):
    def page(self, pageid, text):
        return {"pageid": pageid, "title": f"T{pageid}", "extract": text,
                "revisions": [{"revid": 7}]}

    def test_only_prose_in_the_length_band_is_usable(self):
        long_enough = PROSE + "x" * fetch_wikipedia.MIN_CHARS
        self.assertEqual(fetch_wikipedia.usable(self.page(1, long_enough)), long_enough.strip())
        self.assertIsNone(fetch_wikipedia.usable(self.page(1, "short")))
        self.assertIsNone(fetch_wikipedia.usable(
            self.page(1, "\n".join(["a line"] * fetch_wikipedia.MIN_CHARS))))

    def test_a_collection_keeps_each_page_once_and_stops_when_full(self):
        text = PROSE + "x" * fetch_wikipedia.MIN_CHARS
        collection = fetch_wikipedia.Collection("ro", wanted=2)
        self.assertTrue(collection.add([self.page(1, text), self.page(1, text)]))
        self.assertTrue(collection.add([self.page(2, text), self.page(3, text)]))
        self.assertFalse(collection.add([self.page(4, text)]))
        kept = collection.kept
        self.assertEqual([row["pageid"] for row in kept], [1, 2])
        self.assertEqual(kept[0]["url"], "https://ro.wikipedia.org/?curid=1")
        self.assertEqual(kept[0]["revid"], 7)

    def test_a_failed_round_costs_one_request_and_is_retried(self):
        with mock.patch.object(fetch_wikipedia, "candidates",
                               side_effect=urllib.error.URLError("down")), \
                mock.patch.object(fetch_wikipedia.time, "sleep"), \
                mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(fetch_wikipedia.one_round("ro"), (None, 1))
        with mock.patch.object(fetch_wikipedia, "candidates", return_value=[]), \
                mock.patch.object(fetch_wikipedia.time, "sleep"):
            self.assertEqual(fetch_wikipedia.one_round("ro"), ([], 2))


class DatasetTests(unittest.TestCase):
    def test_only_the_set_asked_for_is_fetched(self):
        with mock.patch.object(get_datasets, "get_flores") as flores, \
                mock.patch.object(get_datasets, "get_per_language") as per_language, \
                mock.patch.object(get_datasets, "get_coding") as coding:
            get_datasets.fetch_sets(Path("."), ["ron_Latn"], "sib")
            self.assertFalse(flores.called or coding.called)
            self.assertEqual(per_language.call_args.args[2], "sib200")
            get_datasets.fetch_sets(Path("."), ["ron_Latn"], None)
            self.assertTrue(flores.called and coding.called)

    def test_the_sources_come_from_the_data_file(self):
        self.assertEqual(get_datasets.DATASETS["sources"][0]["name"], "FLORES-200")
        self.assertIn("{code}", get_datasets.SIB_FILE)


class OversizeTests(unittest.TestCase):
    def test_a_negative_layer_count_leaves_the_split_to_llama_cpp(self):
        with mock.patch.object(measure_oversize, "setting", return_value="8099") as setting:
            automatic = measure_oversize.server_command("srv", "m.gguf", -1, 4096)
            forced = measure_oversize.server_command("srv", "m.gguf", 20, 4096)
        setting.assert_called_with("oversize_port")
        self.assertNotIn("--n-gpu-layers", automatic)
        self.assertEqual(automatic[automatic.index("--port") + 1], "8099")
        self.assertEqual(forced[-2:], ["--n-gpu-layers", "20"])


class NightTests(unittest.TestCase):
    def night(self, **flags):
        out = Path(tempfile.mkdtemp())
        arguments = argparse.Namespace(python="py", data="data", home="home", out=str(out),
                                       skip_reload=False, only_new=False, ladders_only=False,
                                       skip_throughput=True, **flags)
        return run_all.Night(arguments, io.StringIO()), out

    def test_a_model_that_will_not_start_is_recorded_and_the_night_goes_on(self):
        night, out = self.night()
        with mock.patch.object(run_all, "model_size", return_value=10), \
                mock.patch.object(run_all, "load", return_value={"ok": False, "error": "boom"}), \
                mock.patch("builtins.print"):
            night.model(MODEL)
        entry = json.loads((out / "summary.json").read_text())["text-bulk"]
        self.assertEqual((entry["load"]["error"], entry["size_bytes"]), ("boom", 10))

    def test_a_full_model_runs_every_bench_and_is_unloaded(self):
        night, out = self.night()
        loaded = {"ok": True, "load_s": 1.0}
        with mock.patch.object(run_all, "model_size", return_value=None), \
                mock.patch.object(run_all, "load", return_value=loaded), \
                mock.patch.object(run_all, "unload", return_value={"ok": True, "unload_s": 2}), \
                mock.patch.object(night, "run_bench", return_value={"score": 1}) as bench, \
                mock.patch("builtins.print"):
            night.model(MODEL)
        scripts = [call.args[0].script for call in bench.call_args_list]
        self.assertEqual(scripts, ["bench_classify.py", "bench_comprehension.py",
                                   "bench_translate.py", "bench_coding.py", "bench.py"])
        entry = json.loads((out / "summary.json").read_text())["text-bulk"]
        self.assertEqual((entry["reload"], entry["latency"], entry["unload"]["unload_s"]),
                         (loaded, {"score": 1}, 2))

    def test_the_commands_name_the_server_and_where_to_write(self):
        night, out = self.night()
        latency = night.command(run_all.Bench("bench.py", 1, positional=False), MODEL, out / "x.json")
        self.assertEqual(latency[2:], [f"http://{run_all.LOOPBACK}:1", "text-bulk", str(out / "x.json")])
        longform = night.command(run_all.Bench("bench_longform.py", 8, ("--limit", "60")), MODEL,
                                 out / "y.json")
        self.assertNotIn("--data", longform)
        self.assertEqual(night.command(run_all.Bench("bench_coding.py", 8), MODEL, out / "z.json")[-2:],
                         ["--data", "data"])
