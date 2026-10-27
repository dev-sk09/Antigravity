"""
llm.py - OpenAI-compatible HTTP: GET JSON and a streaming chat client.

One shape works for OpenRouter and any OpenAI-compatible base_url:
  GET  {base_url}/models
  POST {base_url}/chat/completions   (stream: true, SSE chunks)
TLS verifies against $SSL_CERT_FILE (set by the env) when present.
"""
import json
import os
import ssl
import urllib.error
import urllib.request

_CTX = None


def _ctx():
    global _CTX
    if _CTX is None:
        cafile = os.environ.get("SSL_CERT_FILE")
        if cafile and os.path.isfile(cafile):
            _CTX = ssl.create_default_context(cafile=cafile)
        else:
            _CTX = ssl.create_default_context()
    return _CTX


def _headers(provider, extra=None):
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Antigravity-LocalAgent",
    }
    key = provider.get("api_key")
    if key:
        h["Authorization"] = "Bearer " + key
    # OpenRouter asks clients to identify themselves; harmless elsewhere.
    if provider.get("type") == "openrouter":
        h.setdefault("HTTP-Referer", "https://antigravity.local")
        h.setdefault("X-Title", "Antigravity Local Agent")
    for k, v in (provider.get("headers") or {}).items():
        h[k] = v
    for k, v in (extra or {}).items():
        h[k] = v
    return h


class LLMError(Exception):
    pass


def get_json(provider, path, timeout=20):
    url = provider["base_url"].rstrip("/") + path
    req = urllib.request.Request(url, headers=_headers(provider), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _read_err(e)
        raise LLMError("HTTP %s from %s: %s" % (e.code, url, body))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LLMError("request to %s failed: %s" % (url, e))


def chat_stream(provider, model, messages, tools=None, extra=None, timeout=300):
    """Yield parsed OpenAI stream chunk dicts; stops at [DONE]. Raises LLMError."""
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    body = {"model": model, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
    if extra:
        body.update(extra)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(provider), method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ctx())
    except urllib.error.HTTPError as e:
        raise LLMError("HTTP %s from %s: %s" % (e.code, url, _read_err(e)))
    except (urllib.error.URLError, OSError) as e:
        raise LLMError("request to %s failed: %s" % (url, e))
    try:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line or line.startswith(":"):
                continue
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                return
            try:
                yield json.loads(payload)
            except ValueError:
                continue
    finally:
        resp.close()


def _read_err(e):
    try:
        return e.read().decode("utf-8", "replace")[:500]
    except Exception:
        return str(e)
