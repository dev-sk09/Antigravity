/**
 * patches/dm_settings/install.js - watch for the Settings sheet.
 */
var scheduled = false;
var current = null; // settings column decorated by the last scan

// Rows, our head block and our row icons. Adding or removing any of them
// opens, closes or re-renders the Settings home.
var WATCH = '[data-testid^="' + ROW_PREFIX + '"], .dm-set-head, .dm-sico';

function scan() {
  scheduled = false;
  current = null;
  try {
    var first = document.querySelector('[data-testid="settings-nav-item-General"]');
    if (!first || !first.parentElement) return;
    current = first.parentElement;
    decorateList(current);
  } catch (e) {
    try { console.warn('[dmSettings] scan failed', e); } catch (_) {}
  }
}

function scheduleScan() {
  if (scheduled) return;
  scheduled = true;
  (window.requestAnimationFrame || setTimeout)(scan);
}

function touchesSettings(nodes) {
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (n.nodeType === 1 && (n.matches(WATCH) || n.querySelector(WATCH))) return true;
  }
  return false;
}

// A streamed reply or typing mutates the DOM every frame. Only changes inside
// the Settings column, or ones that add or remove its rows, need a rescan.
function onMutations(records) {
  if (scheduled) return;
  for (var i = 0; i < records.length; i++) {
    var r = records[i];
    if ((current && current.contains(r.target))
        || touchesSettings(r.addedNodes) || touchesSettings(r.removedNodes)) {
      scheduleScan();
      return;
    }
  }
}

function install() {
  scan();
  if (window.MutationObserver) {
    new MutationObserver(onMutations).observe(document.documentElement, { childList: true, subtree: true });
    // A theme switch only touches class attributes; refresh the Dark/Light labels.
    var theme = new MutationObserver(function () { if (current) scheduleScan(); });
    theme.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    if (document.body) theme.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }
}
