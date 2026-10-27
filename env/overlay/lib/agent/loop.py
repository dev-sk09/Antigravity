"""
loop.py - one chat turn, optionally with tool calls, emitted as events.

emit(event_dict) is called for each of:
  {type: "token", text}             assistant text delta
  {type: "tool_call", name, args}   model asked to run a tool
  {type: "tool_result", name, ok, output}
  {type: "error", error}
  {type: "done", content, steps}

With tools=None (Phase B) it is a single streamed pass. With tools and a
tool_runner (Phase C) it loops: stream -> run tool_calls -> feed results
back -> stream again, up to max_steps.
"""
from . import llm


def _accumulate(chunks, emit):
    """Consume stream chunks; return (content, tool_calls, finish_reason)."""
    content = []
    tool_calls = {}        # index -> {id, name, arguments}
    finish = None
    for chunk in chunks:
        choices = chunk.get("choices") or []
        if not choices:
            continue
        ch = choices[0]
        delta = ch.get("delta") or {}
        text = delta.get("content")
        if text:
            content.append(text)
            emit({"type": "token", "text": text})
        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            slot = tool_calls.setdefault(idx, {"id": None, "name": "", "arguments": ""})
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["name"] = fn["name"]
            if fn.get("arguments"):
                slot["arguments"] += fn["arguments"]
        if ch.get("finish_reason"):
            finish = ch["finish_reason"]
    ordered = [tool_calls[i] for i in sorted(tool_calls)]
    return "".join(content), ordered, finish


def run_turn(provider, model, messages, emit, tools=None,
             tool_runner=None, extra=None, max_steps=1):
    convo = list(messages)
    last_content = ""
    steps = 0
    try:
        while steps < max_steps:
            steps += 1
            chunks = llm.chat_stream(provider, model, convo, tools=tools, extra=extra)
            content, calls, finish = _accumulate(chunks, emit)
            last_content = content

            if not (calls and tool_runner):
                break

            # Record the assistant's tool request, then run each tool.
            convo.append({
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {"id": c["id"] or ("call_%d" % i), "type": "function",
                     "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                    for i, c in enumerate(calls)
                ],
            })
            for i, c in enumerate(calls):
                name = c["name"]
                emit({"type": "tool_call", "name": name, "args": c["arguments"]})
                ok, output = tool_runner(name, c["arguments"])
                emit({"type": "tool_result", "name": name, "ok": ok, "output": output})
                convo.append({
                    "role": "tool",
                    "tool_call_id": c["id"] or ("call_%d" % i),
                    "name": name,
                    "content": output,
                })
            # loop again so the model can use the results
        emit({"type": "done", "content": last_content, "steps": steps})
    except llm.LLMError as e:
        emit({"type": "error", "error": str(e)})
    except Exception as e:  # never crash the request thread
        emit({"type": "error", "error": "agent loop failed: %s" % e})
