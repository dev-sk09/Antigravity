"""
mock_provider.py - a local OpenAI-compatible provider for offline tests.

GET  /v1/models            -> models_payload (OpenAI or OpenRouter shape)
POST /v1/chat/completions  -> streams the next scripted turn as SSE chunks

Each scripted turn is a list of chunk dicts (OpenAI stream format). With no
script queued it streams a fixed reply. Every request's headers and body are
recorded in .requests for assertions.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_TEXT = ["Hello", " from", " the", " mock", "."]


def text_turn(parts=DEFAULT_TEXT):
    chunks = [{"choices": [{"index": 0, "delta": {"content": p}}]} for p in parts]
    chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    return chunks


def tool_turn(name, args_json, call_id="call_1"):
    """A turn where the model asks for one tool, arguments split across chunks."""
    half = len(args_json) // 2
    return [
        {"choices": [{"index": 0, "delta": {"tool_calls": [
            {"index": 0, "id": call_id, "type": "function",
             "function": {"name": name, "arguments": args_json[:half]}}]}}]},
        {"choices": [{"index": 0, "delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": args_json[half:]}}]}}]},
        {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
    ]


class MockProvider:
    def __init__(self, models_payload=None, status=200):
        self.models_payload = models_payload or {"data": [{"id": "mock-model"}]}
        self.status = status
        self.scripts = []
        self.requests = []
        self._lock = threading.Lock()
        owner = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _record(self, body=None):
                with owner._lock:
                    owner.requests.append({"path": self.path, "headers": dict(self.headers),
                                           "body": body})

            def do_GET(self):
                self._record()
                if self.path.rstrip("/").endswith("/models"):
                    data = json.dumps(owner.models_payload).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n).decode() or "{}")
                self._record(body)
                if owner.status != 200:
                    data = b'{"error":{"message":"bad key"}}'
                    self.send_response(owner.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                with owner._lock:
                    turn = owner.scripts.pop(0) if owner.scripts else text_turn()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                for c in turn:
                    self.wfile.write(("data: " + json.dumps(c) + "\n\n").encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.base_url = "http://127.0.0.1:%d/v1" % self.port
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
