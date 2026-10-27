# Local Agent sidecar (`agy-agent`)

A second, self-contained agent that runs beside the built-in Gemini core. The
core (`language_server`) is a closed binary that talks only to Google, so it
cannot be pointed at other providers. This sidecar adds an **additional** mode:
use OpenRouter, or any OpenAI-compatible endpoint (base URL + API key + model),
with a tool-using loop. It does not change the core or its model picker.

## Launch

`bin/agy-agent start [--port N] [--foreground]` · `stop` · `status`.
Double-forks like `agy-daemon` (PID at `$HOME/.gemini/antigravity-app/agent/agent.pid`).
Binds `127.0.0.1` only and **refuses to start without a token** — from
`$AGY_AGENT_TOKEN` or a `0600` `--token-file`, never argv. `CoreServerService`
starts/stops it and passes the per-launch token (shared with the System
Gateway) and `--port BuildConfig.AGENT_PORT` (default 45264 / dev 45265).

## HTTP API (bearer token on every route)

`Authorization: Bearer <token>` or `X-AGY-Agent-Token`; fail-closed.

| Route | Purpose |
|---|---|
| `GET /health` | liveness + current selection |
| `GET /providers` · `POST /providers` · `DELETE /providers/<id>` | manage providers (keys redacted on read) |
| `POST /select {provider, model}` | set the active model |
| `GET /models?provider=<id>&refresh=1` | live list, normalized (id, name, context, prices, `free`) |
| `GET/POST /settings` | tools on/off, `allow_shell`, allowed roots, limits |
| `POST /chat {messages, provider?, model?, tools?}` | SSE: `token` / `tool_call` / `tool_result` / `error` / `done` |

## Modules
- `server.py` — routing + bearer auth (`ThreadingHTTPServer`).
- `providers.py` — `providers.json` (0600); UI sees redacted records; keys are
  attached to provider requests server-side, never exposed to the page.
- `models.py` — `{base_url}/models`, OpenAI + OpenRouter shapes, 60 s cache.
- `llm.py` — streaming `{base_url}/chat/completions` client (TLS via `$SSL_CERT_FILE`).
- `loop.py` — one turn: stream → run tool calls → feed results back → repeat (≤ `max_steps`).
- `tools.py` — `read_file`/`write_file`/`list_dir` and `device` (via the Java
  gateway); `run_command` only when `allow_shell` is on. Every path is confined
  to an allowed root; output is truncated.
- `settings.py` — defaults: file + device tools on, **shell off**, roots = project dir + `$HOME`.

## Config & state
`$HOME/.gemini/antigravity-app/agent/`: `providers.json` (0600), `settings.json`,
`conversations/`, `agent.log`, `agent.pid`.

## Tests
`env/tests/agent/run_all.sh` — offline, against a mock provider (no network, no
keys): providers CRUD + redaction, model normalization, auth, streamed chat,
tool round-trip, path confinement, shell default-off.
