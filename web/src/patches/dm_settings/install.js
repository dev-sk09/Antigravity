/**
 * patches/dm_settings/install.js - watch for the Settings sheet.
 */
var scheduled = false;

function scan() {
  scheduled = false;
  try {
    var first = document.querySelector('[data-testid="settings-nav-item-General"]');
    if (!first || !first.parentElement) return;
    decorateList(first.parentElement);
  } catch (e) {
    try { console.warn('[dmSettings] scan failed', e); } catch (_) {}
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
