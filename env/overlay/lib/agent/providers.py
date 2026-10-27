"""
providers.py - stored model providers (OpenAI-compatible) + the selected model.

A provider is {id, name, type, base_url, api_key, headers, default_model}. The
file (providers.json, 0600) also holds {"selected": {"provider": id, "model": m}}.
Reads for the UI are redacted (api_key -> bool have_key + masked hint).
"""
import re
import time

from . import paths

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(name):
    s = _SLUG.sub("-", (name or "").lower()).strip("-")
    return s or ("provider-" + str(int(time.time())))


def _blank():
    return {"providers": [], "selected": {}}


def _load():
    data = paths.load_json(paths.PROVIDERS_FILE, None)
    if not isinstance(data, dict) or "providers" not in data:
        return _blank()
    if not isinstance(data.get("providers"), list):
        data["providers"] = []
    if not isinstance(data.get("selected"), dict):
        data["selected"] = {}
    return data


def _save(data):
    paths.save_json(paths.PROVIDERS_FILE, data, private=True)


def _mask(key):
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "..." + key[-4:]


def redact(p):
    out = {k: p.get(k) for k in ("id", "name", "type", "base_url", "default_model")}
    out["have_key"] = bool(p.get("api_key"))
    out["key_hint"] = _mask(p.get("api_key"))
    out["headers"] = dict(p.get("headers") or {})
    return out


def list_providers():
    data = _load()
    return {
        "providers": [redact(p) for p in data["providers"]],
        "selected": data.get("selected", {}),
    }


def get_provider(pid):
    """Full record including api_key, or None. Internal use only."""
    for p in _load()["providers"]:
        if p.get("id") == pid:
            return p
    return None


def get_selected():
    """(provider_record, model) for the current selection, or (None, None)."""
    data = _load()
    sel = data.get("selected") or {}
    pid = sel.get("provider")
    if not pid:
        return None, None
    for p in data["providers"]:
        if p.get("id") == pid:
            return p, sel.get("model") or p.get("default_model")
    return None, None


def upsert(spec):
    """Add or update a provider. Returns the redacted record."""
    name = (spec.get("name") or "").strip()
    base_url = (spec.get("base_url") or "").strip().rstrip("/")
    if not name:
        raise ValueError("provider needs a name")
    if not base_url:
        raise ValueError("provider needs a base_url")
    ptype = (spec.get("type") or "openai").strip().lower()
    pid = (spec.get("id") or "").strip() or _slug(name)

    data = _load()
    existing = next((p for p in data["providers"] if p.get("id") == pid), None)
    if existing is None:
        existing = {"id": pid}
        data["providers"].append(existing)

    existing["name"] = name
    existing["type"] = ptype
    existing["base_url"] = base_url
    existing["default_model"] = (spec.get("default_model") or "").strip()
    existing["headers"] = dict(spec.get("headers") or {})
    # Only overwrite the key when a new one is supplied; empty string clears it.
    if "api_key" in spec and spec["api_key"] is not None:
        existing["api_key"] = spec["api_key"]
    elif "api_key" not in existing:
        existing["api_key"] = ""

    _save(data)
    return redact(existing)


def delete(pid):
    data = _load()
    before = len(data["providers"])
    data["providers"] = [p for p in data["providers"] if p.get("id") != pid]
    if (data.get("selected") or {}).get("provider") == pid:
        data["selected"] = {}
    _save(data)
    return len(data["providers"]) < before


def select(pid, model=None):
    data = _load()
    if not any(p.get("id") == pid for p in data["providers"]):
        raise ValueError("unknown provider: " + str(pid))
    data["selected"] = {"provider": pid, "model": (model or "").strip()}
    _save(data)
    return data["selected"]
