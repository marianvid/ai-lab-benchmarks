"""Where AI-Lab is, from configuration, and the calls every study makes to it."""

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from harness.shared import lab


class Manager(BaseHTTPRequestHandler):
    """A stand-in manager: two instances, one running; loads fail for `broken`."""

    def do_GET(self):
        self._send(200, [{"id": "asr", "running": True}, {"id": "idle", "running": False}])

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        if self.path.endswith("/broken/load"):
            self._send(200, {"ok": False, "error": "no room"})
        elif self.path.startswith("/v1/"):
            self._send(200, {"content_type": self.headers["Content-Type"], "size": len(body)})
        else:
            self._send(200, {"ok": True, "total_ms": 12})

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


class SettingsTests(unittest.TestCase):
    def config(self, values: dict) -> dict:
        path = Path(tempfile.mkdtemp()) / "config.json"
        path.write_text(json.dumps(values))
        return {lab.CONFIG_VARIABLE: str(path)}

    def test_the_manager_comes_from_the_argument_the_environment_or_the_configuration(self):
        with mock.patch.dict(os.environ, self.config({"port": 8123}), clear=True):
            self.assertEqual(lab.manager_url(), f"http://{lab.LOOPBACK}:8123")
            self.assertEqual(lab.manager_url("http://given"), "http://given")
        with mock.patch.dict(os.environ, {**self.config({"port": 1}),
                                          lab.MANAGER_VARIABLE: "http://env"}, clear=True):
            self.assertEqual(lab.manager_url(), "http://env")
        with mock.patch.dict(os.environ, self.config(
                {"benchmark": {"manager_url": "http://configured"}}), clear=True):
            self.assertEqual(lab.manager_url(), "http://configured")

    def test_a_missing_setting_stops_the_study_naming_it(self):
        with mock.patch.dict(os.environ, self.config({"benchmark": {}}), clear=True), \
                self.assertRaisesRegex(lab.MissingSetting, "benchmark.scratch_dir"):
            lab.setting("scratch_dir")
        with mock.patch.dict(os.environ, {}, clear=True), \
                self.assertRaisesRegex(lab.MissingSetting, lab.CONFIG_VARIABLE):
            lab.configuration()

    def test_a_setting_is_read(self):
        with mock.patch.dict(os.environ, self.config({"benchmark": {"scratch_dir": "/x"}}),
                             clear=True):
            self.assertEqual(lab.setting("scratch_dir"), "/x")


class CallTests(unittest.TestCase):
    server: ThreadingHTTPServer
    base: str

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer((lab.LOOPBACK, 0), Manager)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://{lab.LOOPBACK}:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_running_instances_are_unloaded(self):
        self.assertEqual(lab.unload_running(self.base), [{"instance": "asr", "ok": True}])

    def test_load_and_unload_are_timed(self):
        loaded = lab.timed(self.base, "asr", "load")
        self.assertEqual((loaded["ok"], loaded["manager_total_ms"]), (True, 12))
        refused = lab.timed(self.base, "broken", "load")
        self.assertEqual((refused["ok"], refused["error"]), (False, "no room"))
        self.assertFalse(lab.unreachable(refused))
        gone = lab.timed(f"http://{lab.LOOPBACK}:1", "asr", "load")
        self.assertTrue(lab.unreachable(gone))

    def test_a_form_carries_the_fields_and_the_file(self):
        answer = lab.multipart(self.base + "/v1/audio/transcriptions", {"model": "asr"},
                               ("file", "clip.wav", b"RIFF...."))
        self.assertTrue(answer["content_type"].startswith("multipart/form-data; boundary="))
        body, kind = lab.form_body({"model": "ocr"}, ("file", "page.png", b"\x89PNG"))
        self.assertIn(b"Content-Type: image/png", body)
        self.assertIn(b'name="model"', body)
        self.assertTrue(kind.startswith("multipart/form-data"))

    def test_json_is_written_in_one_step(self):
        path = Path(tempfile.mkdtemp()) / "deep" / "out.json"
        lab.write_json(path, {"ă": 1})
        self.assertEqual(json.loads(path.read_text()), {"ă": 1})
        self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_an_error_is_described(self):
        self.assertEqual(lab.read_error(ValueError("bad")), "ValueError: bad")
