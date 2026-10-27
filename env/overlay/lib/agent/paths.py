"""
paths.py - config locations and atomic JSON helpers for the local agent.

State lives under $HOME/.gemini/antigravity-app/agent, next to the daemon's
own dir. Secrets (providers.json) are written 0600.
"""
import json
import os
import tempfile

HOME = os.environ.get("HOME") or os.path.expanduser("~")
AGENT_DIR = os.path.join(HOME, ".gemini", "antigravity-app", "agent")
PROVIDERS_FILE = os.path.join(AGENT_DIR, "providers.json")
SETTINGS_FILE = os.path.join(AGENT_DIR, "settings.json")
CONV_DIR = os.path.join(AGENT_DIR, "conversations")
LOG_FILE = os.path.join(AGENT_DIR, "agent.log")
PID_FILE = os.path.join(AGENT_DIR, "agent.pid")


def ensure_dir():
    os.makedirs(AGENT_DIR, exist_ok=True)
    os.makedirs(CONV_DIR, exist_ok=True)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data, private=False):
    """Atomic write; private=True clamps the file to 0600 before the rename."""
    ensure_dir()
    fd, tmp = tempfile.mkstemp(dir=AGENT_DIR, prefix=".tmp-")
    try:
        if private:
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
