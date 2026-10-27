"""
tools.py - the tools the model may call, and the runner that executes them.

Safety model:
  * Every path is resolved and must sit inside an allowed root (settings:
    the project dir and $HOME by default). No escaping via .. or symlinks.
  * File + device tools are available when tools_enabled.
  * run_command is only offered and only runs when allow_shell is explicitly
    turned on; it runs in an allowed root with a timeout and truncated output.
  * device actions are forwarded to the Java System Gateway with its token.
Each tool returns (ok: bool, output: str); output is truncated to max_output.
"""
import json
import os
import subprocess
import urllib.request

from . import settings as settings_mod


# ---- path confinement -------------------------------------------------------
def _inside_roots(path, roots):
    real = os.path.realpath(path)
    for root in roots:
        if real == root or real.startswith(root + os.sep):
            return real
    return None


def _resolve(path, roots):
    if not isinstance(path, str) or not path:
        raise ValueError("path required")
    if not os.path.isabs(path):
        base = roots[0] if roots else os.environ.get("HOME", "/")
        path = os.path.join(base, path)
    real = _inside_roots(path, roots)
    if real is None:
        raise PermissionError("path is outside the allowed folders: " + path)
    return real


# ---- file tools -------------------------------------------------------------
def _read_file(args, cfg, roots):
    real = _resolve(args.get("path"), roots)
    with open(real, "r", encoding="utf-8", errors="replace") as f:
        return True, f.read(cfg["max_output"] + 1)


def _write_file(args, cfg, roots):
    real = _resolve(args.get("path"), roots)
    content = args.get("content")
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    parent = os.path.dirname(real)
    if _inside_roots(parent, roots) is None:
        raise PermissionError("parent folder is outside the allowed folders")
    os.makedirs(parent, exist_ok=True)
    with open(real, "w", encoding="utf-8") as f:
        f.write(content)
    return True, "wrote %d bytes to %s" % (len(content.encode("utf-8")), real)


def _list_dir(args, cfg, roots):
    real = _resolve(args.get("path") or (roots[0] if roots else "."), roots)
    entries = []
    for name in sorted(os.listdir(real)):
        full = os.path.join(real, name)
        entries.append(name + ("/" if os.path.isdir(full) else ""))
    return True, "\n".join(entries)


# ---- shell tool (opt-in) ----------------------------------------------------
def _shell_argv(cmd):
    """Prefer the env's bash (login shell, for termux-exec), else any sh."""
    prefix = os.environ.get("PREFIX", "")
    for sh, flag in ((os.path.join(prefix, "bin", "bash"), "-lc"),
                     ("/system/bin/sh", "-c"),
                     ("/bin/bash", "-lc"),
                     ("/bin/sh", "-c")):
        if sh and os.path.isfile(sh):
            return [sh, flag, cmd]
    return ["sh", "-c", cmd]


def _run_command(args, cfg, roots):
    cmd = args.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("command required")
    cwd = roots[0] if roots else os.environ.get("HOME")
    argv = _shell_argv(cmd)
    try:
        proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=cfg["command_timeout"],
                              text=True)
        out = proc.stdout or ""
        return proc.returncode == 0, "exit=%d\n%s" % (proc.returncode, out)
    except subprocess.TimeoutExpired:
        return False, "command timed out after %ss" % cfg["command_timeout"]


# ---- device tool (via the Java gateway) -------------------------------------
def _gateway():
    home = os.environ.get("HOME", "")
    port, token = "", os.environ.get("AGY_GATEWAY_TOKEN", "")
    # The port file is authoritative: the gateway rewrites it if it had to
    # fall back to another port. Fall back to the env hint only if absent.
    if home:
        try:
            with open(os.path.join(home, "logs", "gateway.port")) as f:
                port = f.read().strip()
        except OSError:
            pass
    if not port:
        port = os.environ.get("AGY_GATEWAY_PORT", "")
    if not token and home:
        try:
            with open(os.path.join(home, "logs", "gateway.token")) as f:
                token = f.read().strip()
        except OSError:
            pass
    return port, token


def _device(args, cfg, roots):
    action = args.get("action")
    allowed = {"notify", "toast", "clipboard", "clipboard_set", "open_url", "system_info", "vibrate"}
    if action not in allowed:
        raise ValueError("unknown device action: %s" % action)
    port, token = _gateway()
    if not port or not token:
        return False, "device gateway not available"
    payload = dict(args.get("params") or {})
    body = json.dumps({"command": action, "payload": payload}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%s/gateway" % port, data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, resp.read().decode("utf-8")
    except Exception as e:
        return False, "device call failed: %s" % e


# ---- specs + runner ---------------------------------------------------------
def _f(name, description, properties, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


_FILE_SPECS = [
    _f("read_file", "Read a UTF-8 text file inside the allowed folders.",
       {"path": {"type": "string"}}, ["path"]),
    _f("write_file", "Create or overwrite a UTF-8 text file inside the allowed folders.",
       {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _f("list_dir", "List the entries of a directory inside the allowed folders.",
       {"path": {"type": "string"}}, []),
    _f("device", "Perform a device action via the app (notify, toast, clipboard, "
       "open_url, system_info, vibrate).",
       {"action": {"type": "string"}, "params": {"type": "object"}}, ["action"]),
]
_SHELL_SPEC = _f("run_command",
                 "Run a shell command in the project folder and return its output. "
                 "Only available when the user has enabled shell access.",
                 {"command": {"type": "string"}}, ["command"])

_HANDLERS = {
    "read_file": _read_file, "write_file": _write_file, "list_dir": _list_dir,
    "device": _device, "run_command": _run_command,
}


def build_tools(cfg):
    if not cfg.get("tools_enabled"):
        return []
    specs = list(_FILE_SPECS)
    if cfg.get("allow_shell"):
        specs.append(_SHELL_SPEC)
    return specs


def make_runner(cfg, roots):
    def runner(name, args_json):
        if name not in _HANDLERS:
            return False, "unknown tool: %s" % name
        if name == "run_command" and not cfg.get("allow_shell"):
            return False, "shell access is disabled"
        try:
            args = json.loads(args_json) if isinstance(args_json, str) and args_json.strip() else {}
        except ValueError:
            return False, "could not parse tool arguments as JSON"
        try:
            ok, out = _HANDLERS[name](args, cfg, roots)
        except (PermissionError, ValueError) as e:
            return False, str(e)
        except Exception as e:
            return False, "%s failed: %s" % (name, e)
        if isinstance(out, str) and len(out) > cfg["max_output"]:
            out = out[:cfg["max_output"]] + "\n...[truncated]"
        return ok, out
    return runner


def factory(body):
    """Server hook: (tools_spec, runner, max_steps) for one chat turn.

    A request may pass "tools": false to force a plain chat with no tools.
    """
    cfg = settings_mod.load()
    if body.get("tools") is False:
        return None, None, 1
    roots = settings_mod.allowed_roots(cfg)
    tools = build_tools(cfg)
    if not tools:
        return None, None, 1
    return tools, make_runner(cfg, roots), max(1, int(cfg.get("max_steps", 8)))
