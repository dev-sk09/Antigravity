/**
 * patches/dm_home/install.js - watch for the Home list.
 */
var scheduled = false;

function scan() {
  scheduled = false;
  try {
    var list = document.querySelector(SEL_LIST);
    if (list) decorateHome(list);
    decorateTitle(!!list);
  } catch (e) {
    try { console.warn('[dmHome] scan failed', e); } catch (_) {}
  }
}

function scheduleScan() {
  if (scheduled) return;
  scheduled = true;
  (window.requestAnimationFrame || setTimeout)(scan);
}

function install() {
  scan();
  if (window.MutationObserver) {
    new MutationObserver(scheduleScan).observe(document.documentElement, { childList: true, subtree: true });
  }
}
