"""
settings.py - Local Agent tool settings (settings.json).

Conservative defaults: file + device tools on, shell OFF. Tools operate only
within allowed_roots (defaults: the active project dir and $HOME). The user
turns shell on explicitly from the panel; nothing here is a remote shell by
default.
"""
import os

from . import paths

_DEFAULTS = {
    "tools_enabled": True,     # expose file/device tools to the model
    "allow_shell": False,      # the run_command tool (off until the user opts in)
    "allowed_roots": [],       # extra roots beyond the defaults below
    "command_timeout": 60,     # seconds per run_command
    "max_output": 20000,       # chars kept from any tool's output
    "max_steps": 8,            # tool-call rounds per chat turn
}


def load():
    data = paths.load_json(paths.SETTINGS_FILE, {})
    out = dict(_DEFAULTS)
    if isinstance(data, dict):
        for k in _DEFAULTS:
            if k in data:
                out[k] = data[k]
    return out


def save(patch):
    data = load()
    for k in _DEFAULTS:
        if k in patch:
            data[k] = patch[k]
    paths.save_json(paths.SETTINGS_FILE, data)
    return data


def default_roots():
    roots = []
    project = os.environ.get("AGY_PROJECT_DIR")
    if project and os.path.isdir(project):
        roots.append(project)
    home = os.environ.get("HOME")
    if home and os.path.isdir(home):
        roots.append(home)
    return roots


def allowed_roots(cfg=None):
    cfg = cfg or load()
    roots = list(default_roots())
    for r in cfg.get("allowed_roots") or []:
        if isinstance(r, str) and os.path.isdir(r):
            roots.append(r)
    # Canonical, de-duplicated.
    seen, out = set(), []
    for r in roots:
        real = os.path.realpath(r)
        if real not in seen:
            seen.add(real)
            out.append(real)
    return out
