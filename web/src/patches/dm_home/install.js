/**
 * patches/dm_home/install.js - watch for the Home list.
 */
var scheduled = false;
var current = null; // conversation list decorated by the last scan

// The list, the top-bar settings button and our own nodes. Adding or removing
// any of them switches between Home and a conversation, or means React
// re-rendered something we decorate.
var WATCH = SEL_LIST + ', ' + SEL_SETTINGS +
  ', .dm-hero, .dm-home-head, .dm-dr-backdrop, .dm-menu, .dm-ws-title';

function scan() {
  scheduled = false;
  try {
    var list = document.querySelector(SEL_LIST);
    current = list;
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

function touchesHome(nodes) {
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (n.nodeType === 1 && (n.matches(WATCH) || n.querySelector(WATCH))) return true;
  }
  return false;
}

// A streamed reply or typing mutates the DOM every frame. Only changes inside
// the task list (rows, status spinners), or ones that add or remove the nodes
// in WATCH, need a rescan.
function onMutations(records) {
  if (scheduled) return;
  for (var i = 0; i < records.length; i++) {
    var r = records[i];
    if ((current && current.contains(r.target))
        || touchesHome(r.addedNodes) || touchesHome(r.removedNodes)) {
      scheduleScan();
      return;
    }
  }
}

function install() {
  scan();
  if (window.MutationObserver) {
    new MutationObserver(onMutations).observe(document.documentElement, { childList: true, subtree: true });
  }
}
