/**
 * patches/web_optimizations/sheet_scroll.js - scroll areas inside bottom
 * sheets that overflow get data-base-ui-swipe-ignore, so a vertical swipe
 * scrolls them instead of dragging the sheet.
 */
function installSheetScroll(doc) {
  if (doc.__agSheetScroll) return;
  doc.__agSheetScroll = true;
  var SHEET = '[data-testid="bottom-sheet"]';
  var SCROLLERS = '.overflow-y-auto, .overflow-auto, .scrollable';
  var view = doc.defaultView || window;
  var open = 0; // sheets found by the last sync
  function sync(root) {
    try {
      var sheets = root.querySelectorAll(SHEET);
      open = sheets.length;
      for (var i = 0; i < sheets.length; i++) {
        var scrollers = sheets[i].querySelectorAll(SCROLLERS);
        for (var j = 0; j < scrollers.length; j++) {
          var el = scrollers[j];
          var overflows = el.scrollHeight > el.clientHeight + 2;
          if (overflows && !el.hasAttribute('data-base-ui-swipe-ignore')) {
            el.setAttribute('data-base-ui-swipe-ignore', '');
          } else if (!overflows && el.hasAttribute('data-base-ui-swipe-ignore')) {
            el.removeAttribute('data-base-ui-swipe-ignore');
          }
        }
      }
    } catch (e) {}
  }
  var pending = false;
  function schedule() {
    if (pending) return;
    pending = true;
    // Read scroll sizes at the start of the next frame, where layout is clean
    // or about to run anyway, instead of forcing an extra layout mid-frame.
    (view.requestAnimationFrame || setTimeout)(function () {
      pending = false;
      sync(doc);
    });
  }
  function touchesSheet(nodes) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.nodeType === 1 && (n.matches(SHEET) || n.querySelector(SHEET))) return true;
    }
    return false;
  }
  // Overflow only changes when a sheet comes or goes or its content changes;
  // mutations elsewhere (a streaming reply) are ignored.
  function onMutations(records) {
    if (pending) return;
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if ((open && r.target.closest && r.target.closest(SHEET))
          || touchesSheet(r.addedNodes) || touchesSheet(r.removedNodes)) {
        schedule();
        return;
      }
    }
  }
  sync(doc);
  try {
    var target = doc.getElementById('root') || doc.body || doc.documentElement;
    if (view && view.MutationObserver && target) {
      new view.MutationObserver(onMutations).observe(target, { childList: true, subtree: true });
    }
  } catch (e) {}
}
