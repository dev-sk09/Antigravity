"""
server.py - loopback HTTP API for the local agent. Bearer-token on every route.

Routes:
  GET    /health
  GET    /providers
  POST   /providers              {name, type, base_url, api_key, ...}
  DELETE /providers/<id>
  POST   /select                 {provider, model}
  GET    /models?provider=<id>&refresh=1
  POST   /chat                   {messages, provider?, model?, extra?}  -> SSE
"""
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import models as models_mod
from . import providers as providers_mod
from . import loop as loop_mod
from . import settings as settings_mod

VERSION = "1.0.0"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AgyAgent/" + VERSION

    # -- helpers ------------------------------------------------------------
    def _authorized(self):
        token = getattr(self.server, "auth_token", "") or ""
        if not token:
            return False
        got = self.headers.get("Authorization", "")
        if got[:7].lower() == "bearer ":
            got = got[7:].strip()
        if not got:
            got = self.headers.get("X-AGY-Agent-Token", "")
        return bool(got) and hmac.compare_digest(str(got), str(token))

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return {}
        if n <= 0 or n > 8 * 1024 * 1024:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            return {}

    def _cors(self):
        # Loopback + token-gated; the WebView page is a different origin/port,
        # so CORS must be permitted for the panel to reach the sidecar at all.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")

    def do_OPTIONS(self):
        # Preflight carries no Authorization header, so it is answered unauthenticated.
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def _json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _sse_open(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

    def _sse(self, obj):
        try:
            self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, OSError):
            raise _ClientGone()

    def log_message(self, *a):
        pass

    # -- dispatch -----------------------------------------------------------
    def do_GET(self):
        if not self._authorized():
            return self._json(401, {"ok": False, "error": "unauthorized"})
        u = urlparse(self.path)
        if u.path == "/health":
            prov, model = providers_mod.get_selected()
            return self._json(200, {"ok": True, "version": VERSION,
                                    "selected": {"provider": prov.get("id") if prov else None,
                                                 "model": model}})
        if u.path == "/providers":
            return self._json(200, {"ok": True, **providers_mod.list_providers()})
        if u.path == "/settings":
            cfg = settings_mod.load()
            return self._json(200, {"ok": True, "settings": cfg,
                                    "allowed_roots": settings_mod.allowed_roots(cfg)})
        if u.path == "/models":
            q = parse_qs(u.query)
            pid = (q.get("provider") or [None])[0]
            refresh = (q.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            prov = providers_mod.get_provider(pid) if pid else providers_mod.get_selected()[0]
            if not prov:
                return self._json(404, {"ok": False, "error": "no such provider"})
            try:
                return self._json(200, {"ok": True, "provider": prov.get("id"),
                                        "models": models_mod.list_models(prov, refresh=refresh)})
            except Exception as e:
                return self._json(502, {"ok": False, "error": str(e)})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_DELETE(self):
        if not self._authorized():
            return self._json(401, {"ok": False, "error": "unauthorized"})
        u = urlparse(self.path)
        if u.path.startswith("/providers/"):
            pid = u.path[len("/providers/"):]
            ok = providers_mod.delete(pid)
            models_mod.invalidate(pid)
            return self._json(200 if ok else 404, {"ok": ok})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {"ok": False, "error": "unauthorized"})
        u = urlparse(self.path)
        if u.path == "/providers":
            try:
                rec = providers_mod.upsert(self._body())
                models_mod.invalidate(rec["id"])
                return self._json(200, {"ok": True, "provider": rec})
            except ValueError as e:
                return self._json(400, {"ok": False, "error": str(e)})
        if u.path == "/select":
            b = self._body()
            try:
                sel = providers_mod.select(b.get("provider"), b.get("model"))
                return self._json(200, {"ok": True, "selected": sel})
            except ValueError as e:
                return self._json(400, {"ok": False, "error": str(e)})
        if u.path == "/settings":
            cfg = settings_mod.save(self._body())
            return self._json(200, {"ok": True, "settings": cfg,
                                    "allowed_roots": settings_mod.allowed_roots(cfg)})
        if u.path == "/chat":
            return self._chat(self._body())
        return self._json(404, {"ok": False, "error": "not found"})

    def _chat(self, body):
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            return self._json(400, {"ok": False, "error": "messages required"})
        pid = body.get("provider")
        if pid:
            prov = providers_mod.get_provider(pid)
            model = body.get("model") or (prov or {}).get("default_model")
        else:
            prov, model = providers_mod.get_selected()
            model = body.get("model") or model
        if not prov:
            return self._json(400, {"ok": False, "error": "no provider selected"})
        if not model:
            return self._json(400, {"ok": False, "error": "no model selected"})

        self._sse_open()
        tools, runner, max_steps = self.server.tool_support(body)
        try:
            loop_mod.run_turn(prov, model, messages, self._sse,
                              tools=tools, tool_runner=runner,
                              extra=body.get("extra"), max_steps=max_steps)
        except _ClientGone:
            pass


class _ClientGone(Exception):
    pass


class AgentServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host, port, auth_token):
        super().__init__((host, port), Handler)
        self.auth_token = auth_token
        self._tool_factory = None

    def set_tool_factory(self, factory):
        """factory(body) -> (tools_spec, tool_runner, max_steps). Set in Phase C."""
        self._tool_factory = factory

    def tool_support(self, body):
        if self._tool_factory is None:
            return None, None, 1
        return self._tool_factory(body)


def serve(host, port, auth_token, tool_factory=None):
    srv = AgentServer(host, port, auth_token)
    if tool_factory is not None:
        srv.set_tool_factory(tool_factory)
    t = threading.Thread(target=srv.serve_forever, name="AgentServer", daemon=True)
    t.start()
    return srv
