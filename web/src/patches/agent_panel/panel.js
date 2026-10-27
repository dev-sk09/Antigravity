/**
 * patches/agent_panel/panel.js - overlay shell, tabs, launcher button.
 */
var panelEl = null;
var fabEl = null;
var views = {};
var headerSub = null;

var TABS = [
  { id: 'chat', label: 'Chat', render: renderChat },
  { id: 'models', label: 'Models', render: renderModels },
  { id: 'providers', label: 'Providers', render: renderProviders },
  { id: 'settings', label: 'Settings', render: renderSettings }
];

function updateHeader() {
  if (headerSub) {
    headerSub.textContent = state.selected.model
      ? state.selected.model
      : 'no model selected';
  }
}

function switchTab(id) {
  state.tab = id;
  TABS.forEach(function (t) {
    views[t.id].parentNode.classList.toggle('agx-active', t.id === id);
    views[t.id].tabBtn.classList.toggle('agx-active', t.id === id);
  });
  var t = TABS.filter(function (x) { return x.id === id; })[0];
  if (t) t.render(views[id]);
}

function buildPanel() {
  if (panelEl) return;
  panelEl = el('div', 'agx-panel');

  var head = el('div', 'agx-head');
  var icon = el('span', null, ICON_BOT);
  icon.style.width = '22px'; icon.style.height = '22px';
  head.appendChild(icon);
  var titleWrap = el('div', 'agx-grow');
  titleWrap.appendChild(el('div', 'agx-title', 'Local Agent'));
  headerSub = el('div', 'agx-sep', 'no model selected');
  titleWrap.appendChild(headerSub);
  head.appendChild(titleWrap);
  var x = el('button', 'agx-x', '✕');
  x.addEventListener('click', closePanel);
  head.appendChild(x);
  panelEl.appendChild(head);

  var tabs = el('div', 'agx-tabs');
  var body = el('div', 'agx-body');
  TABS.forEach(function (t) {
    var btn = el('button', 'agx-tab', t.label);
    btn.addEventListener('click', function () { switchTab(t.id); });
    tabs.appendChild(btn);
    var view = el('div', 'agx-view');
    var inner = el('div');
    view.appendChild(inner);
    body.appendChild(view);
    views[t.id] = inner;
    inner.tabBtn = btn;
  });
  panelEl.appendChild(tabs);
  panelEl.appendChild(body);
  document.body.appendChild(panelEl);
}

function openPanel() {
  buildPanel();
  panelEl.classList.add('agx-open');
  // Refresh providers/selection, then render the current tab.
  loadProviders().then(function () {
    updateHeader();
    switchTab(state.tab);
  }).catch(function () {
    switchTab(state.tab);
  });
}

function closePanel() {
  if (panelEl) panelEl.classList.remove('agx-open');
}

function buildFab() {
  if (fabEl) return;
  fabEl = el('button', 'agx-fab');
  fabEl.setAttribute('aria-label', 'Open Local Agent');
  fabEl.innerHTML = ICON_BOT;
  fabEl.addEventListener('click', openPanel);
  document.body.appendChild(fabEl);
}
