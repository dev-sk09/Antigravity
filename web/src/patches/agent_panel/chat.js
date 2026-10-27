/**
 * patches/agent_panel/chat.js - streamed chat, with tool calls shown inline.
 */
function renderChat(root) {
  clear(root);
  var wrap = el('div', 'agx-chat');

  var top = el('div', 'agx-row');
  top.appendChild(el('div', 'agx-grow agx-muted',
    state.selected.model ? ('Model: ' + state.selected.model) : 'No model selected (Models tab)'));
  var toolsWrap = el('label', 'agx-row');
  var toolsCb = el('input'); toolsCb.type = 'checkbox'; toolsCb.checked = state.useTools;
  toolsCb.addEventListener('change', function () { state.useTools = toolsCb.checked; });
  toolsWrap.appendChild(toolsCb);
  toolsWrap.appendChild(el('span', 'agx-muted', 'Tools'));
  top.appendChild(toolsWrap);
  wrap.appendChild(top);

  var msgs = el('div', 'agx-msgs');
  wrap.appendChild(msgs);

  var composer = el('div', 'agx-composer');
  var ta = el('textarea', 'agx-textarea agx-grow'); ta.rows = 2;
  ta.placeholder = 'Message the local agent...';
  var send = el('button', 'agx-btn', 'Send');
  composer.appendChild(ta);
  composer.appendChild(send);
  wrap.appendChild(composer);
  root.appendChild(wrap);

  function bubble(role, text) {
    var b = el('div', 'agx-msg ' + (role === 'user' ? 'agx-user' : 'agx-asst'));
    b.textContent = text;
    msgs.appendChild(b);
    msgs.scrollTop = msgs.scrollHeight;
    return b;
  }

  // Replay existing conversation.
  state.messages.forEach(function (m) {
    if (m.role === 'user' || m.role === 'assistant') bubble(m.role, m.content || '');
  });

  function doSend() {
    var text = ta.value.trim();
    if (!text || state.streaming) return;
    if (!state.selected.model) { bubble('assistant', '[Select a model in the Models tab first]'); return; }
    ta.value = '';
    state.messages.push({ role: 'user', content: text });
    bubble('user', text);

    state.streaming = true;
    send.disabled = true;
    var asst = bubble('assistant', '');
    var acc = '';
    var body = { messages: state.messages.slice() };
    if (!state.useTools) body.tools = false;

    chatStream(body, function (ev) {
      if (ev.type === 'token') {
        acc += ev.text; asst.textContent = acc; msgs.scrollTop = msgs.scrollHeight;
      } else if (ev.type === 'tool_call') {
        var t = el('div', 'agx-tool'); t.textContent = '⚙ ' + ev.name + '(' + (ev.args || '') + ')';
        msgs.insertBefore(t, asst); msgs.scrollTop = msgs.scrollHeight;
      } else if (ev.type === 'tool_result') {
        var r = el('div', 'agx-tool');
        r.appendChild(el('div', null, (ev.ok ? '✓ ' : '✗ ') + ev.name));
        var pre = el('pre'); pre.textContent = String(ev.output || '').slice(0, 4000);
        r.appendChild(pre);
        msgs.insertBefore(r, asst); msgs.scrollTop = msgs.scrollHeight;
      } else if (ev.type === 'error') {
        var e = el('div', 'agx-err'); e.textContent = 'Error: ' + ev.error;
        msgs.insertBefore(e, asst);
      } else if (ev.type === 'done') {
        if (ev.content != null && !acc) { acc = ev.content; asst.textContent = acc; }
      }
    }).catch(function (e) {
      var er = el('div', 'agx-err'); er.textContent = 'Request failed: ' + (e.message || e);
      msgs.appendChild(er);
    }).then(function () {
      state.streaming = false;
      send.disabled = false;
      if (acc) state.messages.push({ role: 'assistant', content: acc });
    });
  }

  send.addEventListener('click', doSend);
  ta.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
  });
}
