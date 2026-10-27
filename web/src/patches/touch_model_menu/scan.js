/**
 * patches/touch_model_menu/scan.js - DOM scan for effort groups.
 */

function scan() {
  var groups = [];
  try {
    groups = document.querySelectorAll(CONFIG.effortGroup);
  } catch (_) {
    groups = [];
  }
  state.groups = groups.length;
  for (var i = 0; i < groups.length; i++) {
    var group = groups[i];
    var row = (group.closest && group.closest(CONFIG.menuItemRole)) || group.parentElement || group;
    registerRow(row);
  }
}

// Only an added node that is or contains an effort group can need a new row
// handler. A streaming reply mutates the DOM every frame and never adds one,
// so it no longer triggers periodic full-document scans.
function bringsEffortGroup(records) {
  for (var i = 0; i < records.length; i++) {
    var added = records[i].addedNodes;
    for (var j = 0; j < added.length; j++) {
      var n = added[j];
      if (n.nodeType === 1
          && (n.matches(CONFIG.effortGroup) || n.querySelector(CONFIG.effortGroup))) {
        return true;
      }
    }
  }
  return false;
}

function scheduleScan() {
  if (state.scanTimer) return;
  // Next frame, so the handler is in place before the new row can be tapped.
  state.scanTimer = (window.requestAnimationFrame || setTimeout)(function () {
    state.scanTimer = 0;
    scan();
  });
}

function onMutations(records) {
  if (!state.scanTimer && bringsEffortGroup(records)) scheduleScan();
}
