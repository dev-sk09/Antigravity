/**
 * patches/agent_panel/models.js - live model list, free filter, switch model.
 */
function renderModels(root) {
  clear(root);

  if (!state.providers.length) {
    root.appendChild(el('div', 'agx-muted', 'Add a provider first (Providers tab).'));
    return;
  }

  // Provider selector (defaults to the selected one, else the first).
  if (!state.modelsProvider) {
    state.modelsProvider = state.selected.provider || state.providers[0].id;
  }
  var bar = el('div', 'agx-card');
  bar.appendChild(el('label', 'agx-label', 'Provider'));
  var sel = el('select', 'agx-select');
  state.providers.forEach(function (p) {
    var o = el('option', null, p.name); o.value = p.id;
    if (p.id === state.modelsProvider) o.selected = true;
    sel.appendChild(o);
  });
  sel.addEventListener('change', function () {
    state.modelsProvider = sel.value;
    state.models = [];
    load(false);
  });
  bar.appendChild(sel);

  var controls = el('div', 'agx-row'); controls.style.marginTop = '8px';
  var search = el('input', 'agx-input agx-grow'); search.type = 'search';
  search.placeholder = 'Search models'; search.value = state.modelFilter;
  search.addEventListener('input', function () { state.modelFilter = search.value; paint(); });
  controls.appendChild(search);
  var freeWrap = el('label', 'agx-row');
  var free = el('input'); free.type = 'checkbox'; free.checked = state.freeOnly;
  free.addEventListener('change', function () { state.freeOnly = free.checked; paint(); });
  freeWrap.appendChild(free);
  freeWrap.appendChild(el('span', 'agx-muted', 'Free only'));
  controls.appendChild(freeWrap);
  var refresh = el('button', 'agx-btn agx-ghost', 'Refresh');
  refresh.addEventListener('click', function () { load(true); });
  controls.appendChild(refresh);
  bar.appendChild(controls);
  root.appendChild(bar);

  var status = el('div', 'agx-muted'); status.style.margin = '6px 2px';
  root.appendChild(status);
  var listCard = el('div', 'agx-card');
  root.appendChild(listCard);

  function paint() {
    clear(listCard);
    var q = state.modelFilter.trim().toLowerCase();
    var rows = state.models.filter(function (m) {
      if (state.freeOnly && !m.free) return false;
      if (q && (m.id + ' ' + (m.name || '')).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    status.textContent = rows.length + ' / ' + state.models.length + ' models'
      + (state.selected.model ? ' · active: ' + state.selected.model : '');
    if (!rows.length) {
      listCard.appendChild(el('div', 'agx-muted', 'No models.'));
      return;
    }
    rows.slice(0, 500).forEach(function (m) {
      var it = el('div', 'agx-mitem'
        + (state.selected.provider === state.modelsProvider && state.selected.model === m.id ? ' agx-chosen' : ''));
      var info = el('div', 'agx-grow');
      info.appendChild(el('div', 'agx-mid', m.id));
      var meta = [];
      if (m.context) meta.push((m.context / 1000).toFixed(0) + 'k ctx');
      if (m.prompt_price != null) meta.push('$' + m.prompt_price + '/tok in');
      if (meta.length) info.appendChild(el('div', 'agx-muted', meta.join(' · ')));
      it.appendChild(info);
      if (m.free) it.appendChild(el('span', 'agx-badge agx-mfree', 'free'));
      it.addEventListener('click', function () {
        api('POST', '/select', { provider: state.modelsProvider, model: m.id }).then(function (j) {
          state.selected = j.selected || state.selected;
          paint();
          updateHeader();
        });
      });
      listCard.appendChild(it);
    });
  }

  function load(refreshLive) {
    status.textContent = 'Loading models...';
    clear(listCard);
    api('GET', '/models?provider=' + encodeURIComponent(state.modelsProvider)
      + (refreshLive ? '&refresh=1' : '')).then(function (j) {
      state.models = j.models || [];
      paint();
    }).catch(function (e) {
      status.textContent = '';
      clear(listCard);
      listCard.appendChild(el('div', 'agx-err', 'Could not load models: ' + (e.message || e)));
    });
  }

  if (state.models.length) { paint(); } else { load(false); }
}
