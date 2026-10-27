"""
models.py - live model listing, normalized across providers.

Normalized row: {id, name, context, prompt_price, completion_price, free}.
A short in-process cache keeps the UI's repeated refreshes cheap.
"""
import time

from . import llm

_CACHE = {}          # provider_id -> (ts, rows)
_TTL = 60.0


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize(raw, ptype):
    mid = raw.get("id") or raw.get("name") or ""
    name = raw.get("name") or mid
    ctx = raw.get("context_length") or raw.get("context_window")
    top = raw.get("top_provider") or {}
    if ctx is None and isinstance(top, dict):
        ctx = top.get("context_length")
    pricing = raw.get("pricing") or {}
    prompt_price = _to_float(pricing.get("prompt"))
    completion_price = _to_float(pricing.get("completion"))
    free = False
    if mid.endswith(":free"):
        free = True
    elif prompt_price == 0 and completion_price == 0 and pricing:
        free = True
    return {
        "id": mid,
        "name": name,
        "context": ctx,
        "prompt_price": prompt_price,
        "completion_price": completion_price,
        "free": free,
    }


def list_models(provider, refresh=False):
    pid = provider.get("id")
    now = time.time()
    if not refresh and pid in _CACHE:
        ts, rows = _CACHE[pid]
        if now - ts < _TTL:
            return rows
    data = llm.get_json(provider, "/models")
    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = []
    rows = [_normalize(m, provider.get("type")) for m in items if isinstance(m, dict)]
    rows.sort(key=lambda r: (not r["free"], r["id"]))
    _CACHE[pid] = (now, rows)
    return rows


def invalidate(pid=None):
    if pid is None:
        _CACHE.clear()
    else:
        _CACHE.pop(pid, None)
