function installSheetScroll(doc) {
  if (doc.__agSheetScroll) return;
  doc.__agSheetScroll = true;
  var SHEET = '[data-testid="bottom-sheet"]';
  var SCROLLERS = '.overflow-y-auto, .overflow-auto, .scrollable';
  function sync(root) {
    try {
      var sheets = root.querySelectorAll(SHEET);
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
  var timer = 0;
  function schedule() {
    if (timer) return;
    timer = setTimeout(function () { timer = 0; sync(doc); }, 120);
  }
  sync(doc);
  try {
    var view = doc.defaultView || window;
    var target = doc.getElementById('root') || doc.body || doc.documentElement;
    if (view && view.MutationObserver && target) {
      new view.MutationObserver(schedule).observe(target, { childList: true, subtree: true });
    }
  } catch (e) {}
}
installSheetScroll(window.document);
