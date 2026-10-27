#!/usr/bin/env python3
"""
test_tools.py - offline tests for the tool layer and the tool-using loop.

  python3 env/tests/agent/test_tools.py
"""
import json
import os
import sys
import tempfile
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
_HOME = tempfile.mkdtemp(prefix="agy-tools-test-")
os.environ["HOME"] = _HOME
os.environ.pop("SSL_CERT_FILE", None)
# Confine tools to a dedicated project dir for the test.
_PROJECT = tempfile.mkdtemp(prefix="agy-proj-")
os.environ["AGY_PROJECT_DIR"] = _PROJECT
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "overlay", "lib")))
sys.path.insert(0, HERE)

from agent import providers, server, settings, tools  # noqa: E402
from mock_provider import MockProvider, text_turn, tool_turn  # noqa: E402

TOKEN = "tok"


def reset():
    for f in (os.path.join(_HOME, ".gemini", "antigravity-app", "agent", "providers.json"),
              os.path.join(_HOME, ".gemini", "antigravity-app", "agent", "settings.json")):
        try:
            os.unlink(f)
        except OSError:
            pass


class PathConfinementTest(unittest.TestCase):
    def setUp(self):
        reset()
        self.roots = [os.path.realpath(_PROJECT)]

    def test_write_then_read_inside_root(self):
        runner = tools.make_runner(settings.load(), self.roots)
        ok, out = runner("write_file", json.dumps({"path": "notes/a.txt", "content": "hi"}))
        self.assertTrue(ok, out)
        self.assertTrue(os.path.isfile(os.path.join(_PROJECT, "notes", "a.txt")))
        ok, out = runner("read_file", json.dumps({"path": "notes/a.txt"}))
        self.assertTrue(ok)
        self.assertEqual(out, "hi")

    def test_escape_is_blocked(self):
        runner = tools.make_runner(settings.load(), self.roots)
        for path in ("../../etc/passwd", "/etc/passwd", os.path.join(_PROJECT, "..", "x")):
            ok, out = runner("read_file", json.dumps({"path": path}))
            self.assertFalse(ok)
            self.assertIn("allowed folders", out)

    def test_symlink_escape_blocked(self):
        link = os.path.join(_PROJECT, "escape")
        try:
            os.symlink("/etc", link)
        except OSError:
            self.skipTest("symlinks unsupported")
        runner = tools.make_runner(settings.load(), self.roots)
        ok, out = runner("read_file", json.dumps({"path": "escape/hostname"}))
        self.assertFalse(ok)
        self.assertIn("allowed folders", out)

    def test_output_truncated(self):
        big = "x" * 50000
        with open(os.path.join(_PROJECT, "big.txt"), "w") as f:
            f.write(big)
        cfg = dict(settings.load())
        cfg["max_output"] = 100
        ok, out = tools.make_runner(cfg, self.roots)("read_file", json.dumps({"path": "big.txt"}))
        self.assertTrue(ok)
        self.assertTrue(out.endswith("[truncated]"))
        self.assertLessEqual(len(out), 100 + 20)


class ShellGateTest(unittest.TestCase):
    def setUp(self):
        reset()
        self.roots = [os.path.realpath(_PROJECT)]

    def test_shell_off_by_default(self):
        cfg = settings.load()
        self.assertFalse(cfg["allow_shell"])
        self.assertNotIn("run_command", [s["function"]["name"] for s in tools.build_tools(cfg)])
        ok, out = tools.make_runner(cfg, self.roots)("run_command", json.dumps({"command": "echo hi"}))
        self.assertFalse(ok)
        self.assertIn("disabled", out)

    def test_shell_runs_when_enabled(self):
        cfg = dict(settings.load())
        cfg["allow_shell"] = True
        names = [s["function"]["name"] for s in tools.build_tools(cfg)]
        self.assertIn("run_command", names)
        ok, out = tools.make_runner(cfg, self.roots)("run_command", json.dumps({"command": "echo marker-42"}))
        self.assertTrue(ok, out)
        self.assertIn("marker-42", out)
        # It ran inside the project root.
        ok, out = tools.make_runner(cfg, self.roots)("run_command", json.dumps({"command": "pwd"}))
        self.assertIn(os.path.realpath(_PROJECT), out)


def sse_events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


class LoopTest(unittest.TestCase):
    def setUp(self):
        reset()
        self.mock = MockProvider()
        # Server WITH the real tool factory, so tools are exercised end to end.
        self.srv = server.serve("127.0.0.1", 0, TOKEN, tool_factory=tools.factory)
        self.port = self.srv.server_address[1]
        self._add_and_select()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.mock.close()

    def _call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     data=data, method=method)
        req.add_header("Authorization", "Bearer " + TOKEN)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()

    def _add_and_select(self):
        self._call("POST", "/providers", {"id": "m", "name": "M", "base_url": self.mock.base_url,
                                           "api_key": "k"})
        self._call("POST", "/select", {"provider": "m", "model": "mock-model"})

    def test_tool_call_round_trip(self):
        # Model: ask write_file, then (after the tool result) give a final answer.
        self.mock.scripts.append(tool_turn("write_file",
                                            json.dumps({"path": "out.txt", "content": "DATA"})))
        self.mock.scripts.append(text_turn(["Saved", " it."]))
        status, body = self._call("POST", "/chat",
                                  {"messages": [{"role": "user", "content": "save DATA to out.txt"}]})
        self.assertEqual(status, 200)
        ev = sse_events(body)
        types = [e["type"] for e in ev]
        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)
        tc = next(e for e in ev if e["type"] == "tool_call")
        self.assertEqual(tc["name"], "write_file")
        tr = next(e for e in ev if e["type"] == "tool_result")
        self.assertTrue(tr["ok"])
        self.assertEqual(ev[-1]["type"], "done")
        self.assertEqual("".join(e["text"] for e in ev if e["type"] == "token"), "Saved it.")
        self.assertEqual(open(os.path.join(_PROJECT, "out.txt")).read(), "DATA")
        # The second provider request carried the tool result back.
        second = [r for r in self.mock.requests if r["path"].endswith("/chat/completions")][-1]
        roles = [m["role"] for m in second["body"]["messages"]]
        self.assertIn("tool", roles)

    def test_tools_false_forces_plain_chat(self):
        self.mock.scripts.append(tool_turn("write_file", json.dumps({"path": "x", "content": "y"})))
        status, body = self._call("POST", "/chat",
                                  {"messages": [{"role": "user", "content": "hi"}], "tools": False})
        ev = sse_events(body)
        # No tools offered, so the loop makes a single pass and does not execute anything.
        self.assertNotIn("tool_result", [e["type"] for e in ev])
        sent = [r for r in self.mock.requests if r["path"].endswith("/chat/completions")][0]
        self.assertNotIn("tools", sent["body"])

    def test_settings_endpoint_round_trip(self):
        status, body = self._call("GET", "/settings")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["settings"]["allow_shell"])
        status, body = self._call("POST", "/settings", {"allow_shell": True})
        self.assertTrue(json.loads(body)["settings"]["allow_shell"])
        # Offered tools now include run_command.
        self.assertTrue(settings.load()["allow_shell"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
