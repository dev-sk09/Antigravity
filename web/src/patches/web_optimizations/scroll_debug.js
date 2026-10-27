/**
 * patches/web_optimizations/scroll_debug.js - TEMPORARY scroll diagnostics.
 *
 * Logs one "[AGY ScrollDbg]" line per touch gesture (visible in logcat under
 * AGY_JS): which layout is open, the touched element, every ancestor up to
 * <body> with its overflow / touch-action / scroll sizes, whether any
 * touchmove was default-prevented, and whether anything actually scrolled.
 * Remove this file from src.manifest once the scroll bug is understood.
 */
function describeEl(el) {
  if (!el || !el.tagName) return String(el);
  var s = el.tagName.toLowerCase();
  if (el.id) s += '#' + el.id;
  var tid = el.getAttribute && el.getAttribute('data-testid');
  if (tid) s += '[' + tid + ']';
  var role = el.getAttribute && el.getAttribute('role');
  if (role) s += '{' + role + '}';
  var cls = (typeof el.className === 'string' ? el.className : '').trim();
  if (cls) s += '.' + cls.split(/\s+/).slice(0, 4).join('.');
  return s;
}

function ancestorChain(el) {
  var out = [];
  var n = 0;
  while (el && el.nodeType === 1 && n < 25) {
    var cs = window.getComputedStyle(el);
    var scrollable = (cs.overflowY === 'auto' || cs.overflowY === 'scroll') &&
        el.scrollHeight > el.clientHeight;
    out.push((scrollable ? '*SCROLLABLE* ' : '') + describeEl(el) +
        ' oy=' + cs.overflowY + ' ta=' + cs.touchAction +
        ' sh=' + el.scrollHeight + ' ch=' + el.clientHeight +
        ' st=' + el.scrollTop + ' pe=' + cs.pointerEvents +
        (el.hasAttribute('inert') ? ' INERT' : '') +
        (el.hasAttribute('data-base-ui-swipe-ignore') ? ' SWIPE-IGNORE' : ''));
    el = el.parentElement;
    n++;
  }
  return out;
}

function installScrollDebug(global, doc) {
  try {
    var g = null;
    doc.addEventListener('touchstart', function (e) {
      var t = e.touches[0];
      g = {
        target: e.target,
        x: t ? Math.round(t.clientX) : -1,
        y: t ? Math.round(t.clientY) : -1,
        moves: 0,
        prevented: 0,
        scrolled: {}
      };
    }, { capture: true, passive: true });

    // Window bubble phase runs after every other listener, so defaultPrevented
    // reflects what the app's own handlers decided.
    global.addEventListener('touchmove', function (e) {
      if (!g) return;
      g.moves++;
      if (e.defaultPrevented) g.prevented++;
    }, { passive: true });

    doc.addEventListener('scroll', function (e) {
      if (g) g.scrolled[describeEl(e.target)] = 1;
    }, { capture: true, passive: true });

    global.addEventListener('touchend', function () {
      if (!g || g.moves < 3) { g = null; return; }
      var info = {
        ua: navigator.userAgent.slice(0, 80),
        vw: global.innerWidth + 'x' + global.innerHeight,
        sheet: !!doc.querySelector('[data-testid="bottom-sheet"]'),
        modal: !!doc.querySelector('.settings-modal-container'),
        at: g.x + ',' + g.y,
        moves: g.moves,
        prevented: g.prevented,
        scrolled: Object.keys(g.scrolled),
        chain: ancestorChain(g.target)
      };
      console.log('[AGY ScrollDbg] ' + JSON.stringify(info));
      g = null;
    }, { passive: true });
    console.log('[AGY ScrollDbg] installed');
  } catch (e) {}
}
