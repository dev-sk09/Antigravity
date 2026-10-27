/**
 * patches/agent_panel/providers.js - add/switch/remove providers.
 */
function loadProviders() {
  return api('GET', '/providers').then(function (j) {
    state.providers = j.providers || [];
    state.selected = j.selected || {};
  });
}

function renderProviders(root) {
  clear(root);

  var list = el('div', 'agx-card agx-plist');
  if (!state.providers.length) {
    list.appendChild(el('div', 'agx-muted', 'No providers yet. Add one below.'));
  }
  state.providers.forEach(function (p) {
    var item = el('div', 'agx-pitem');
    var info = el('div', 'agx-grow');
    info.appendChild(el('div', null, p.name));
    info.appendChild(el('div', 'agx-muted', p.type + ' · ' + p.base_url
      + (p.have_key ? ' · key ' + p.key_hint : ' · no key')));
    item.appendChild(info);
    if (state.selected.provider === p.id) {
      item.appendChild(el('span', 'agx-badge agx-sel', 'active'));
    }
    var del = el('button', 'agx-btn agx-ghost', '✕');
    del.addEventListener('click', function () {
      api('DELETE', '/providers/' + encodeURIComponent(p.id)).then(function () {
        return loadProviders();
      }).then(function () { renderProviders(root); });
    });
    item.appendChild(del);
    list.appendChild(item);
  });
  root.appendChild(list);

  // Add / edit form
  var form = el('div', 'agx-card');
  form.appendChild(el('div', null, '<b>Add a provider</b>'));

  var presets = el('div', 'agx-row');
  presets.style.flexWrap = 'wrap';
  presets.style.margin = '8px 0';
  PRESETS.forEach(function (ps) {
    var b = el('button', 'agx-btn agx-ghost', ps.name);
    b.addEventListener('click', function () {
      fName.value = ps.name;
      fType.value = ps.type;
      fUrl.value = ps.base_url;
    });
    presets.appendChild(b);
  });
  form.appendChild(presets);

  form.appendChild(el('label', 'agx-label', 'Name'));
  var fName = el('input', 'agx-input'); fName.type = 'text'; fName.placeholder = 'My provider';
  form.appendChild(fName);

  form.appendChild(el('label', 'agx-label', 'Type'));
  var fType = el('select', 'agx-select');
  ['openrouter', 'openai'].forEach(function (t) {
    var o = el('option', null, t); o.value = t; fType.appendChild(o);
  });
  form.appendChild(fType);

  form.appendChild(el('label', 'agx-label', 'Base URL'));
  var fUrl = el('input', 'agx-input'); fUrl.type = 'url';
  fUrl.placeholder = 'https://openrouter.ai/api/v1';
  form.appendChild(fUrl);

  form.appendChild(el('label', 'agx-label', 'API key / token'));
  var fKey = el('input', 'agx-input'); fKey.type = 'password'; fKey.placeholder = 'sk-...';
  form.appendChild(fKey);

  form.appendChild(el('label', 'agx-label', 'Default model (optional)'));
  var fModel = el('input', 'agx-input'); fModel.type = 'text';
  fModel.placeholder = 'e.g. meta-llama/llama-3.1-8b-instruct:free';
  form.appendChild(fModel);

  var err = el('div', 'agx-err'); err.style.display = 'none';
  form.appendChild(err);

  var save = el('button', 'agx-btn', 'Save provider');
  save.style.marginTop = '10px';
  save.addEventListener('click', function () {
    err.style.display = 'none';
    var spec = {
      name: fName.value, type: fType.value, base_url: fUrl.value,
      api_key: fKey.value, default_model: fModel.value
    };
    save.disabled = true;
    api('POST', '/providers', spec).then(function () {
      return loadProviders();
    }).then(function () {
      save.disabled = false;
      renderProviders(root);
    }).catch(function (e) {
      save.disabled = false;
      err.textContent = String(e.message || e);
      err.style.display = 'block';
    });
  });
  form.appendChild(save);
  root.appendChild(form);
}
