"""The text benchmarks: how they read their sets and mark the answers."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import (bench, bench_agentic, bench_classify, bench_coding, bench_comprehension,
                bench_longform, evalcommon)


class FakeRun(evalcommon.Run):
    """An `evalcommon.Run` that answers every request with `answer`, sending nothing."""

    def __init__(self, answer):
        super().__init__("http://unused", "fake", 1)
        self.answer = answer

    def ask(self, messages, max_tokens, temperature=0.0):
        return self.answer


class CommonTests(unittest.TestCase):
    def test_scratch_work_is_removed_even_when_cut_off(self):
        self.assertEqual(evalcommon.strip_think("<think>hm</think> yes"), "yes")
        self.assertEqual(evalcommon.strip_think("still thinking</think>no"), "no")

    def test_f1_is_undefined_without_positives(self):
        self.assertIsNone(evalcommon.f1_scores({"tp": 0, "fp": 1, "tn": 3, "fn": 0})["f1"])
        scores = evalcommon.f1_scores({"tp": 1, "fp": 1, "tn": 2, "fn": 0})
        self.assertEqual((scores["precision"], scores["recall"], scores["f1"]), (0.5, 1.0, 0.6667))

    def test_the_shared_arguments_and_languages(self):
        parsed = evalcommon.arguments_parser("doc").parse_args(["http://x", "label", "4"])
        self.assertEqual((parsed.concurrency, parsed.data, parsed.languages), (4, "./eval-data", None))
        self.assertEqual(evalcommon.language_list(" ro, en"), ["ro", "en"])
        self.assertIsNone(evalcommon.language_list(None))
        with mock.patch("builtins.print") as printed:
            self.assertEqual(evalcommon.nothing_found("questions"), 2)
            evalcommon.banner("L", "m", "3 items")
        self.assertEqual(printed.call_args.args[0], "\n=== L | m | 3 items ===")


class ClassifyTests(unittest.TestCase):
    def test_the_answer_is_found_inside_a_fence(self):
        text = 'Sure:\n```json\n[{"idx": 0, "match": true}, {"idx": 1}]\n```'
        self.assertEqual(bench_classify.parse_answer(text), {0: True})
        self.assertEqual(bench_classify.parse_answer("no array"), {})

    def test_every_answer_falls_in_one_cell(self):
        items = [{"id": "a", "lang": "ro", "category": "politics"},
                 {"id": "b", "lang": "ro", "category": "sports"},
                 {"id": "c", "lang": "en", "category": "politics"}]
        overall, per_language = bench_classify.confusion(
            items, {"a": True, "b": True, "c": False}, "politics")
        self.assertEqual(overall, {"tp": 1, "fp": 1, "tn": 0, "fn": 1})
        self.assertEqual(per_language["en"]["fn"], 1)

    def test_incomplete_rows_are_skipped_and_the_limit_counts_kept_rows(self):
        path = Path(tempfile.mkdtemp()) / "ron_Latn.tsv"
        path.write_text("index\tcategory\ttext\n1\tpolitics\tA vote.\n2\tx\n3\ttravel\tA trip.\n")
        self.assertEqual([row[0] for row in bench_classify.rows_of(path, 2)], ["1", "3"])

    def test_a_batch_records_the_answers_that_came_back(self):
        answers: dict[str, bool] = {}
        run = FakeRun('[{"idx": 1, "match": true}]')
        bench_classify.classify(run, "system", [{"id": "a", "text": "x"},
                                                {"id": "b", "text": "y"}], answers)
        self.assertEqual(answers, {"b": True})
        bench_classify.classify(FakeRun("nothing"), "system", [{"id": "a", "text": "x"}], answers)


class ComprehensionTests(unittest.TestCase):
    def test_a_letter_is_an_answer_and_anything_else_a_miss(self):
        item = {"id": "q", "lang": "ro", "passage": "P", "question": "Q",
                "options": ["a", "b", "c", "d"], "correct": "B"}
        reading = bench_comprehension.Reading(FakeRun("The answer is B."))
        reading.ask(item)
        self.assertEqual(reading.per_language([item]), {"ro": {"n": 1, "accuracy": 1.0}})
        missing = bench_comprehension.Reading(FakeRun("I cannot say"))
        missing.ask(item)
        self.assertEqual(missing.misses[0]["reason"], "no letter in the answer")
        self.assertEqual(missing.run.failed, 1)


class CodingTests(unittest.TestCase):
    def test_both_sets_load_in_one_shape_and_the_broken_problem_is_left_out(self):
        data = Path(tempfile.mkdtemp())
        (data / "coding").mkdir()
        rows = [{"task_id": "HumanEval/32", "prompt": "", "test": "", "entry_point": "f"},
                {"task_id": "HumanEval/0", "prompt": "def f():\n", "test": "def check(c): pass",
                 "entry_point": "f"}]
        (data / "coding" / "humanevalplus.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows))
        (data / "coding" / "mbppplus.jsonl").write_text(json.dumps(
            {"task_id": 2, "prompt": "Write f", "test": "assert f()", "test_list": ["f()"]}) + "\n")
        problems = bench_coding.load(data, "both", None)
        self.assertEqual([p["id"] for p in problems], ["HumanEval/0", "Mbpp/2"])
        self.assertTrue(problems[0]["check"].endswith("check(f)\n"))

    def test_the_longest_code_block_is_the_answer(self):
        text = "```python\nx = 1\n```\nand\n```python\ndef f():\n    return 1\n```"
        self.assertIn("def f", bench_coding.extract_code(text))
        self.assertEqual(bench_coding.extract_code("y = 2"), "y = 2")

    def test_pass_rates_per_set(self):
        results = [{"set": "a", "passed": True}, {"set": "a", "passed": False}]
        self.assertEqual(bench_coding.per_set(results), {"a": {"n": 2, "passed": 1, "pass_rate": 0.5}})
        no_answer = bench_coding.solve(FakeRun(None), {"set": "a", "id": "x", "instruction": ""}, 1)
        self.assertEqual(no_answer["why"], "no answer")


class LongformTests(unittest.TestCase):
    def test_articles_are_filtered_and_limited(self):
        path = Path(tempfile.mkdtemp()) / "articles.jsonl"
        rows = [{"lang": lang, "chars": chars} for lang, chars in
                (("ro", 3000), ("en", 2500), ("ro", 4000), ("ro", 5000))]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        articles = bench_longform.read_articles(path, ["ro"], 2)
        self.assertEqual([row["chars"] for row in articles], [3000, 4000])
        self.assertEqual(bench_longform.lengths_of(articles),
                         {"chars_min": 3000, "chars_median": 4000, "chars_max": 4000})


class AgenticTests(unittest.TestCase):
    def test_the_model_cannot_leave_the_repository_or_touch_the_tests(self):
        root = Path(tempfile.mkdtemp()).resolve()
        with self.assertRaises(ValueError):
            bench_agentic.safe_path(root, "../outside")
        self.assertEqual(bench_agentic.write_file(root, "tests/test_x.py", ""),
                         "refused: protected path")
        self.assertEqual(bench_agentic.execute(root, "write_file",
                                               {"path": "src/a.py", "content": "x = 1"}),
                         ("wrote src/a.py", False))
        self.assertEqual(bench_agentic.execute(root, "search", {"query": "x ="}),
                         ("src/a.py:1:x = 1", False))
        self.assertEqual(bench_agentic.execute(root, "finish", {"summary": "done"}), ("done", True))


class LatencyTests(unittest.TestCase):
    def test_the_stream_is_read_to_done_and_bad_lines_are_skipped(self):
        stream = [b'data: {"choices": [{"delta": {"content": "a"}}]}\n', b": ping\n",
                  b"data: not json\n", b'data: {"usage": {"prompt_tokens": 9}}\n',
                  b"data: [DONE]\n", b'data: {"late": true}\n']
        objects = list(bench.events(stream))
        self.assertEqual(len(objects), 2)
        self.assertEqual(bench.pieces(objects[0]), 1)

    def test_speeds_need_a_first_token(self):
        record = bench.speeds("t", {"prompt_tokens": 100, "completion_tokens": 11}, 11, 0.5, 1.5)
        self.assertEqual((record["prefill_tok_s"], record["decode_tok_s"]), (200.0, 10.0))
        self.assertIsNone(bench.speeds("t", {}, 0, None, 1.0)["ttft_s"])

    def test_a_failed_test_is_recorded_not_raised(self):
        with mock.patch.object(bench, "run", side_effect=OSError("refused")):
            self.assertEqual(bench.measure("b", "m", "t", "p", 1), {"test": "t", "error": "OSError('refused')"})
