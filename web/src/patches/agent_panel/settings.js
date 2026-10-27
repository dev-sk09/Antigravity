/**
 * patches/agent_panel/settings.js - tool toggles (shell off by default).
 */
function renderSettings(root) {
  clear(root);
  var card = el('div', 'agx-card');
  card.appendChild(el('div', null, '<b>Tools</b>'));
  card.appendChild(el('div', 'agx-muted',
    'The agent can read and write files and perform device actions inside the '
    + 'allowed folders. Shell access lets it run commands; keep it off unless you '
    + 'trust the model and the task.'));

  var status = el('div', 'agx-muted'); status.style.margin = '8px 0';
  card.appendChild(status);

  var toolsRow = el('div', 'agx-switch');
  toolsRow.appendChild(el('span', null, 'Enable tools (files + device)'));
  var toolsCb = el('input'); toolsCb.type = 'checkbox';
  toolsRow.appendChild(toolsCb);
  card.appendChild(toolsRow);

  var shellRow = el('div', 'agx-switch');
  var shellLabel = el('div');
  shellLabel.appendChild(el('div', null, 'Allow shell commands (run_command)'));
  shellLabel.appendChild(el('div', 'agx-warn', 'Powerful: the model can run commands in the project folder.'));
  shellRow.appendChild(shellLabel);
  var shellCb = el('input'); shellCb.type = 'checkbox';
  shellRow.appendChild(shellCb);
  card.appendChild(shellRow);

  var roots = el('div', 'agx-muted'); roots.style.marginTop = '8px';
  card.appendChild(roots);

  var err = el('div', 'agx-err'); err.style.display = 'none';
  card.appendChild(err);
  root.appendChild(card);

  function save(patch) {
    api('POST', '/settings', patch).catch(function (e) {
      err.textContent = String(e.message || e); err.style.display = 'block';
    }).then(function () { load(); });
  }
  toolsCb.addEventListener('change', function () { save({ tools_enabled: toolsCb.checked }); });
  shellCb.addEventListener('change', function () { save({ allow_shell: shellCb.checked }); });

  function load() {
    api('GET', '/settings').then(function (j) {
      var s = j.settings || {};
      toolsCb.checked = !!s.tools_enabled;
      shellCb.checked = !!s.allow_shell;
      status.textContent = 'Tools ' + (s.tools_enabled ? 'on' : 'off')
        + ' · shell ' + (s.allow_shell ? 'ON' : 'off')
        + ' · max steps ' + (s.max_steps || 8);
      roots.textContent = 'Allowed folders: ' + ((j.allowed_roots || []).join(', ') || '(none)');
    }).catch(function (e) {
      status.textContent = 'Could not load settings: ' + (e.message || e);
    });
  }
  load();
}
