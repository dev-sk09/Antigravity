/**
 * patches/agent_panel/config.js - Local Agent panel: scope, guard, helpers.
 *
 * A separate in-app agent that uses any OpenAI-compatible provider (OpenRouter
 * or any base URL + key + model) via the agy-agent sidecar. First fragment:
 * owns the IIFE scope and exits early if already installed.
 */
'use strict';

if (window.__agAgentPanel && window.__agAgentPanel.__installed) {
  return;
}

var AGENT = window.__AG_AGENT__ || { port: 45264, token: '' };
var AGENT_BASE = 'http://127.0.0.1:' + AGENT.port;

var PRESETS = [
  { name: 'OpenRouter', type: 'openrouter', base_url: 'https://openrouter.ai/api/v1' },
  { name: 'OpenAI', type: 'openai', base_url: 'https://api.openai.com/v1' },
  { name: 'Groq', type: 'openai', base_url: 'https://api.groq.com/openai/v1' },
  { name: 'Together', type: 'openai', base_url: 'https://api.together.xyz/v1' },
  { name: 'Ollama (local)', type: 'openai', base_url: 'http://127.0.0.1:11434/v1' }
];

var state = {
  tab: 'chat',
  providers: [],
  selected: {},
  modelsProvider: null,
  models: [],
  modelFilter: '',
  freeOnly: false,
  messages: [],      // {role, content} for the API
  useTools: true,
  streaming: false
};

function el(tag, cls, html) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function svg(d) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
    + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
}

var ICON_BOT = svg('<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4M9 13h.01M15 13h.01"/>');
