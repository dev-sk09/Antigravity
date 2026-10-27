/**
 * patches/dm_home/decorate.js - build the head block and mark rows/headers.
 */
var STATUS_TEXT = { running: 'Running', waiting: 'Needs you', 'new': 'New', done: '' };

function findHits(q) {
  var seen = {};
  var hits = [];
  document.querySelectorAll(SEL_ROW).forEach(function (row) {
    var a = row.querySelector('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    var title = a.getAttribute('aria-label') || '';
    if (seen[href] || title.toLowerCase().indexOf(q) < 0) return;
    seen[href] = true;
    hits.push({ href: href, title: title, sub: row.getAttribute('data-subtext') || '', st: rowStatus(row) });
  });
  return hits;
}

function renderResults(head, q) {
  q = q.trim().toLowerCase();
  head.toggleAttribute('data-dm-searching', !!q);
  var hits = q ? findHits(q) : [];
  // The list re-renders often (spinners); only rebuild when the results change.
  var key = q + '\n' + JSON.stringify(hits);
  if (head._dmKey === key) return;
  head._dmKey = key;
  var box = head.querySelector('.dm-hs-results');
  box.innerHTML = '';
  if (!q) return;
  hits.forEach(function (h) {
    var item = el('button', 'dm-hs-item');
    item.type = 'button';
    item.setAttribute('data-dm-status', h.st);
    var t = el('span', 'dm-hs-title');
    t.textContent = h.title;
    var sub = el('span', 'dm-hs-sub');
    sub.textContent = h.sub;
    var tag = el('span', 'dm-hs-tag');
    tag.textContent = STATUS_TEXT[h.st];
    item.appendChild(t);
    item.appendChild(sub);
    item.appendChild(tag);
    item.addEventListener('click', function () {
      var live = document.querySelector(SEL_ROW + ' a[href="' + h.href.replace(/"/g, '\\"') + '"]');
      setDrawer(false);
      if (live) live.click();
    });
    box.appendChild(item);
  });
  if (!hits.length) box.appendChild(el('div', 'dm-hs-empty', 'No task matches'));
}

function clearSearch(head) {
  var input = head.querySelector('input');
  input.value = '';
  renderResults(head, '');
}

function focusComposer(text) {
  var input = document.querySelector(SEL_INPUT);
  if (!input) return;
  input.focus();
  // The editor needs a moment after focus before it accepts typed text.
  if (text) setTimeout(function () {
    try { document.execCommand('insertText', false, text); } catch (_) {}
  }, 60);
}

function setDrawer(open) {
  document.documentElement.toggleAttribute('data-dm-drawer', open);
  if (!open) {
    var head = document.querySelector('.dm-home-head');
    if (head) clearSearch(head);
  }
}

function buildHead() {
  var head = el('div', 'dm-home-head');
  var top = el('div', 'dm-dr-top', '<span class="dm-dr-title">Workspace</span>');
  var close = el('button', 'dm-dr-close', ICON_CLEAR);
  close.type = 'button';
  close.setAttribute('aria-label', 'Close task list');
  close.addEventListener('click', function () { setDrawer(false); });
  top.appendChild(close);
  var search = el('label', 'dm-hs', ICON_SEARCH);
  var input = el('input');
  input.type = 'search';
  input.placeholder = 'Search tasks';
  input.setAttribute('aria-label', 'Search tasks');
  var clr = el('button', 'dm-hs-clear', ICON_CLEAR);
  clr.type = 'button';
  clr.setAttribute('aria-label', 'Clear search');
  clr.addEventListener('click', function () { clearSearch(head); input.focus(); });
  input.addEventListener('input', function () { renderResults(head, input.value); });
  input.addEventListener('keydown', function (e) { if (e.key === 'Escape') clearSearch(head); });
  search.appendChild(input);
  search.appendChild(clr);
  head.appendChild(top);
  head.appendChild(search);
  head.appendChild(el('div', 'dm-hs-results'));
  return head;
}

function buildHero() {
  var hero = el('div', 'dm-hero',
    '<div class="dm-hero-logo">' + LOGO + '</div>' +
    '<h1 class="dm-hero-h">What should your agent <span>build today?</span></h1>' +
    '<p class="dm-hero-p">Plan, code, analyze and browse.<br>Sakib runs the task and reports back.</p>');
  var grid = el('div', 'dm-cards');
  CARDS.forEach(function (c) {
    var b = el('button', 'dm-card',
      '<span class="dm-card-i">' + c.i + '</span><span class="dm-card-t"></span><span class="dm-card-s"></span>');
    b.type = 'button';
    b.style.setProperty('--dm-cc', c.c);
    b.querySelector('.dm-card-t').textContent = c.t;
    b.querySelector('.dm-card-s').textContent = c.s;
    b.addEventListener('click', function () { focusComposer(c.p); });
    grid.appendChild(b);
  });
  hero.appendChild(grid);
  return hero;
}

function buildBackdrop() {
  var bd = el('div', 'dm-dr-backdrop');
  bd.addEventListener('click', function () { setDrawer(false); });
  return bd;
}


function decorateHome(list) {
  var wrap = list.parentElement;
  var host = wrap && wrap.parentElement;
  if (!host) return;
  host.setAttribute('data-dm-home', '');
  if (!wrap.hasAttribute('data-dm-list-wrap')) {
    wrap.setAttribute('data-dm-list-wrap', '');
    wrap.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest(SEL_ROW + ' a[href]')) setDrawer(false);
    });
  }
  if (!host.querySelector(':scope > .dm-hero')) host.insertBefore(buildHero(), wrap);
  if (!host.querySelector(':scope > .dm-dr-backdrop')) host.insertBefore(buildBackdrop(), wrap);
  var head = host.querySelector(':scope > .dm-home-head');
  if (!head) host.insertBefore(buildHead(), wrap);
  else if (head.hasAttribute('data-dm-searching')) renderResults(head, head.querySelector('input').value);

  var labels = {};
  list.querySelectorAll('[data-testid="project-header"]').forEach(function (h) {
    var name = h.getAttribute('data-project-label') || '';
    var sec = h.closest('[data-sidebar-section-drop-id]');
    if (sec) labels[sec.getAttribute('data-sidebar-section-drop-id')] = name;
    var c = FOLDER_COLORS[hashName(name) % FOLDER_COLORS.length];
    if (h.style.getPropertyValue('--dm-pc') !== c) h.style.setProperty('--dm-pc', c);
  });
  list.querySelectorAll('[data-sidebar-row-id]').forEach(function (r) {
    var row = r.querySelector(SEL_ROW);
    if (!row) return;
    var proj = labels[r.getAttribute('data-sidebar-section-id')];
    var same = !!proj && row.getAttribute('data-subtext') === proj;
    if (row.hasAttribute('data-dm-same-sub') !== same) row.toggleAttribute('data-dm-same-sub', same);
  });
}

function decorateTitle(onHome) {
  var gear = document.querySelector(SEL_SETTINGS);
  var bar = gear && gear.closest('.justify-between');
  var left = bar && bar.firstElementChild;
  var t = document.querySelector('.dm-ws-title');
  document.documentElement.toggleAttribute('data-dm-hp', onHome && !!left);
  if (onHome && left && !t) {
    var menu = el('button', 'dm-menu', ICON_MENU);
    menu.type = 'button';
    menu.setAttribute('aria-label', 'Open task list');
    menu.addEventListener('click', function () {
      setDrawer(!document.documentElement.hasAttribute('data-dm-drawer'));
    });
    t = el('span', 'dm-ws-title', '<span class="dm-ws-logo">' + LOGO + '</span><span class="dm-ws-name"></span>');
    t.querySelector('.dm-ws-name').textContent = BRAND;
    left.insertBefore(menu, left.firstChild);
    left.appendChild(t);
  } else if (!onHome && t) {
    t.remove();
    var m = document.querySelector('.dm-menu');
    if (m) m.remove();
    setDrawer(false);
  }
}
