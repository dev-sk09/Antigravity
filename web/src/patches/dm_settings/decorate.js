/**
 * patches/dm_settings/decorate.js - per-row decoration and the header block.
 */
var ROW_PREFIX = 'settings-nav-item-';

function rowName(btn) {
  return (btn.getAttribute('data-testid') || '').slice(ROW_PREFIX.length);
}

function decorateRow(btn) {
  var name = rowName(btn);
  var label = btn.querySelector(':scope > span.flex-1') || btn.querySelector(':scope > .flex-col > span');
  if (label) label.setAttribute('data-dm-sub', summaryFor(name));
  if (btn.getAttribute('data-dm') === '1') return;
  btn.setAttribute('data-dm', '1');
  btn.setAttribute('data-dm-row', name);
  if (GROUP_START[name]) btn.setAttribute('data-dm-group', GROUP_START[name]);
  if (ICONS[name]) {
    var ico = document.createElement('span');
    ico.className = 'dm-sico';
    ico.innerHTML = ICONS[name];
    btn.insertBefore(ico, btn.firstChild);
  }
}

function filterRows(list, q) {
  q = (q || '').trim().toLowerCase();
  var rows = list.querySelectorAll('[data-testid^="' + ROW_PREFIX + '"]');
  var shown = 0;
  for (var i = 0; i < rows.length; i++) {
    var name = rowName(rows[i]);
    if (name === 'Account') continue;
    var text = (name + ' ' + summaryFor(name)).toLowerCase();
    var hit = !q || text.indexOf(q) !== -1;
    if (hit) { rows[i].removeAttribute('data-dm-hide'); shown++; }
    else rows[i].setAttribute('data-dm-hide', '');
  }
  list.toggleAttribute('data-dm-filtering', !!q);
  var none = list.querySelector('.dm-none');
  if (none) none.hidden = shown > 0;
}

function syncQuick(head) {
  var ar = head.querySelector('[data-dm-q="autoresume"]');
  if (ar) {
    var on = autoResumeOn();
    ar.classList.toggle('on', on);
    ar.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  var th = head.querySelector('[data-dm-q="theme"] b');
  if (th) th.textContent = isDark() ? 'Dark' : 'Light';
}

function buildHead(list) {
  var head = document.createElement('div');
  head.className = 'dm-set-head';
  head.innerHTML =
    '<label class="dm-search">' + ICON_SEARCH +
    '<input type="search" placeholder="Search settings" autocomplete="off" aria-label="Search settings"></label>' +
    '<div class="dm-quick">' +
    (hasAutoResume()
      ? '<button type="button" class="dm-qk" data-dm-q="autoresume">' + ICON_RETRY + '<span>Auto-resume</span></button>'
      : '') +
    '<button type="button" class="dm-qk" data-dm-q="theme">' + ICONS['Appearance'] + '<span><b>Dark</b> theme</span></button>' +
    '</div>';

  var input = head.querySelector('input');
  input.addEventListener('input', function () { filterRows(list, input.value); });

  head.addEventListener('click', function (e) {
    var q = e.target.closest && e.target.closest('[data-dm-q]');
    if (!q) return;
    if (q.getAttribute('data-dm-q') === 'autoresume') {
      setAutoResume(!autoResumeOn());
      syncQuick(head);
      var gen = list.querySelector('[data-testid="' + ROW_PREFIX + 'General"]');
      if (gen) decorateRow(gen);
    } else {
      // Theme lives in Appearance; open it.
      var app = list.querySelector('[data-testid="' + ROW_PREFIX + 'Appearance"]');
      if (app) app.click();
    }
  });

  var none = document.createElement('div');
  none.className = 'dm-none';
  none.hidden = true;
  none.textContent = 'No setting matches that.';
  head.appendChild(none);
  syncQuick(head);
  return head;
}

function decorateList(list) {
  // list = the upstream column holding the "Settings" title and the rows.
  list.setAttribute('data-dm-settings', '');
  var title = list.firstElementChild;
  var head = list.querySelector(':scope > .dm-set-head');
  if (!head) {
    head = buildHead(list);
    if (title && title.nextSibling) list.insertBefore(head, title.nextSibling);
    else list.appendChild(head);
  } else {
    syncQuick(head);
  }
  var rows = list.ownerDocument.querySelectorAll('[data-testid^="' + ROW_PREFIX + '"]');
  for (var i = 0; i < rows.length; i++) decorateRow(rows[i]);
}
