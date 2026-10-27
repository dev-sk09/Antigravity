/**
 * patches/agent_panel/api.js - talk to the agy-agent sidecar (bearer token).
 */
function api(method, path, body) {
  var opts = {
    method: method,
    headers: { 'Authorization': 'Bearer ' + AGENT.token },
    credentials: 'omit'
  };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  return fetch(AGENT_BASE + path, opts).then(function (r) {
    return r.json().then(function (j) {
      if (!r.ok || (j && j.ok === false)) {
        throw new Error((j && j.error) || ('HTTP ' + r.status));
      }
      return j;
    });
  });
}

/**
 * POST /chat and stream SSE events to onEvent({type,...}). Returns a promise
 * that resolves when the stream ends. Pass an AbortSignal to cancel.
 */
function chatStream(body, onEvent, signal) {
  return fetch(AGENT_BASE + '/chat', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + AGENT.token, 'Content-Type': 'application/json' },
    credentials: 'omit',
    body: JSON.stringify(body),
    signal: signal
  }).then(function (r) {
    if (!r.ok || !r.body) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        onEvent({ type: 'error', error: (j && j.error) || ('HTTP ' + r.status) });
      });
    }
    var reader = r.body.getReader();
    var decoder = new TextDecoder('utf-8');
    var buf = '';
    function pump() {
      return reader.read().then(function (res) {
        if (res.done) {
          flush(buf, true);
          return;
        }
        buf += decoder.decode(res.value, { stream: true });
        var idx;
        while ((idx = buf.indexOf('\n')) >= 0) {
          var line = buf.slice(0, idx);
          buf = buf.slice(idx + 1);
          flush(line, false);
        }
        return pump();
      });
    }
    function flush(line, isTail) {
      line = line.replace(/\r$/, '');
      if (line.indexOf('data:') !== 0) return;
      var payload = line.slice(5).trim();
      if (!payload) return;
      try {
        onEvent(JSON.parse(payload));
      } catch (e) { /* ignore partial/non-JSON */ }
    }
    return pump();
  });
}
