#!/usr/bin/env python3
"""
test_agent.py - offline tests for the Local Agent sidecar (env/overlay/lib/agent).

Runs against a local mock provider: no network, no real keys.
  python3 env/tests/agent/test_agent.py
"""
import json
import os
import stat
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# Config lives under $HOME, so point HOME at a scratch dir before importing.
os.environ["HOME"] = tempfile.mkdtemp(prefix="agy-agent-test-")
os.environ.pop("SSL_CERT_FILE", None)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "overlay", "lib")))
sys.path.insert(0, HERE)

from agent import models, paths, providers, server  # noqa: E402
from mock_provider import MockProvider  # noqa: E402

TOKEN = "test-token-123"


def reset_state():
    for f in (paths.PROVIDERS_FILE, paths.SETTINGS_FILE):
        try:
            os.unlink(f)
        except OSError:
            pass
    models.invalidate()


class ProvidersTest(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_upsert_redacts_key_and_file_is_private(self):
        rec = providers.upsert({"name": "My Router", "type": "openrouter",
                                "base_url": "https://openrouter.ai/api/v1/",
                                "api_key": "sk-or-abcdefghijklmnop"})
        self.assertEqual(rec["id"], "my-router")
        self.assertEqual(rec["base_url"], "https://openrouter.ai/api/v1")
        self.assertTrue(rec["have_key"])
        self.assertNotIn("api_key", rec)
        self.assertEqual(rec["key_hint"], "sk-o...mnop")
        listed = providers.list_providers()
        self.assertNotIn("sk-or-abcdefghijklmnop", json.dumps(listed))
        mode = stat.S_IMODE(os.stat(paths.PROVIDERS_FILE).st_mode)
        self.assertEqual(mode, 0o600)

    def test_update_without_key_keeps_key(self):
        providers.upsert({"id": "p", "name": "P", "base_url": "http://x/v1", "api_key": "secret1"})
        providers.upsert({"id": "p", "name": "P2", "base_url": "http://x/v1"})
        self.assertEqual(providers.get_provider("p")["api_key"], "secret1")
        self.assertEqual(providers.get_provider("p")["name"], "P2")

    def test_validation(self):
        with self.assertRaises(ValueError):
            providers.upsert({"name": "", "base_url": "http://x"})
        with self.assertRaises(ValueError):
            providers.upsert({"name": "n", "base_url": ""})

    def test_select_and_delete_clears_selection(self):
        providers.upsert({"id": "p", "name": "P", "base_url": "http://x/v1"})
        providers.select("p", "m1")
        prov, model = providers.get_selected()
        self.assertEqual((prov["id"], model), ("p", "m1"))
        with self.assertRaises(ValueError):
            providers.select("nope")
        self.assertTrue(providers.delete("p"))
        self.assertEqual(providers.get_selected(), (None, None))


class ModelsTest(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_openrouter_shape_free_detection_and_sort(self):
        payload = {"data": [
            {"id": "openai/gpt-x", "name": "GPT X", "context_length": 128000,
             "pricing": {"prompt": "0.000005", "completion": "0.000015"}},
            {"id": "meta/llama:free", "name": "Llama (free)", "context_length": 8192,
             "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "zero/priced", "pricing": {"prompt": "0", "completion": "0"}},
        ]}
        mock = MockProvider(models_payload=payload)
        try:
            prov = {"id": "or", "type": "openrouter", "base_url": mock.base_url, "api_key": "k"}
            rows = models.list_models(prov)
        finally:
            mock.close()
        ids = [r["id"] for r in rows]
        self.assertEqual(ids[:2], ["meta/llama:free", "zero/priced"])  # free first
        free = {r["id"]: r["free"] for r in rows}
        self.assertTrue(free["meta/llama:free"])
        self.assertTrue(free["zero/priced"])
        self.assertFalse(free["openai/gpt-x"])
        gpt = next(r for r in rows if r["id"] == "openai/gpt-x")
        self.assertEqual(gpt["context"], 128000)
        self.assertAlmostEqual(gpt["prompt_price"], 0.000005)

    def test_openai_shape_ids_only(self):
        mock = MockProvider(models_payload={"object": "list",
                                            "data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]})
        try:
            rows = models.list_models({"id": "oa", "type": "openai", "base_url": mock.base_url})
        finally:
            mock.close()
        self.assertEqual([r["id"] for r in rows], ["gpt-4o", "gpt-4o-mini"])
        self.assertFalse(any(r["free"] for r in rows))


def call(port, method, path, body=None, token=TOKEN):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def sse_events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


class ServerTest(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.mock = MockProvider()
        self.srv = server.serve("127.0.0.1", 0, TOKEN)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.mock.close()

    def test_auth_required(self):
        self.assertEqual(call(self.port, "GET", "/health", token=None)[0], 401)
        self.assertEqual(call(self.port, "GET", "/health", token="wrong")[0], 401)
        status, body = call(self.port, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_empty_token_server_refuses_everything(self):
        srv = server.serve("127.0.0.1", 0, "")
        try:
            self.assertEqual(call(srv.server_address[1], "GET", "/health", token="")[0], 401)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_provider_models_select_and_streamed_chat(self):
        st, body = call(self.port, "POST", "/providers",
                        {"id": "mock", "name": "Mock", "type": "openai",
                         "base_url": self.mock.base_url, "api_key": "provider-key-9"})
        self.assertEqual(st, 200, body)
        self.assertNotIn("provider-key-9", body)

        st, body = call(self.port, "GET", "/models?provider=mock")
        self.assertEqual(st, 200, body)
        self.assertEqual(json.loads(body)["models"][0]["id"], "mock-model")

        st, body = call(self.port, "POST", "/select", {"provider": "mock", "model": "mock-model"})
        self.assertEqual(st, 200, body)

        st, body = call(self.port, "POST", "/chat",
                        {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(st, 200)
        events = sse_events(body)
        text = "".join(e["text"] for e in events if e["type"] == "token")
        self.assertEqual(text, "Hello from the mock.")
        self.assertEqual(events[-1]["type"], "done")
        # The provider key is attached server-side, never sent by the page.
        chat_req = [r for r in self.mock.requests if r["path"].endswith("/chat/completions")][-1]
        self.assertEqual(chat_req["headers"].get("Authorization"), "Bearer provider-key-9")
        self.assertEqual(chat_req["body"]["model"], "mock-model")
        self.assertTrue(chat_req["body"]["stream"])

    def test_provider_error_becomes_error_event(self):
        bad = MockProvider(status=401)
        try:
            call(self.port, "POST", "/providers",
                 {"id": "bad", "name": "Bad", "base_url": bad.base_url, "api_key": "x"})
            call(self.port, "POST", "/select", {"provider": "bad", "model": "m"})
            st, body = call(self.port, "POST", "/chat", {"messages": [{"role": "user", "content": "hi"}]})
        finally:
            bad.close()
        self.assertEqual(st, 200)
        events = sse_events(body)
        self.assertEqual(events[-1]["type"], "error")
        self.assertIn("401", events[-1]["error"])

    def test_chat_needs_selection_and_messages(self):
        self.assertEqual(call(self.port, "POST", "/chat",
                              {"messages": [{"role": "user", "content": "x"}]})[0], 400)
        self.assertEqual(call(self.port, "POST", "/chat", {"messages": []})[0], 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
