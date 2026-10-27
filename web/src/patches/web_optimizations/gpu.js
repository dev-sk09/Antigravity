function installGpu(doc) {
  try {
    if (!doc.querySelector('style[data-agy="gpu-acceleration"]')) {
      var gpu = doc.createElement('style');
      gpu.setAttribute('data-agy', 'gpu-acceleration');
      gpu.textContent =
        'main, [data-testid="autoscroll-viewport"], [data-testid="conversation-view"], [data-testid="chat-container"], .scrollable, .overflow-y-auto, .overflow-auto, [data-drawer-content], [aria-label="Settings"] .overflow-y-auto, [aria-label="Settings"] .overflow-auto, .settings-modal-container .overflow-y-auto, .settings-modal-container .overflow-auto {' +
        ' -webkit-overflow-scrolling: touch !important;' +
        ' overscroll-behavior-y: contain;' +
        ' scroll-behavior: auto !important;' +
        ' touch-action: pan-y;' +
        ' will-change: scroll-position;' +
        ' }' +
        'input, textarea, select, [contenteditable="true"] {' +
        ' touch-action: auto !important;' +
        ' }' +
        '.overflow-x-auto, .overflow-x-auto * {' +
        ' touch-action: pan-x pan-y !important;' +
        ' }' +
        '[data-testid="autoscroll-viewport"] [data-testid="comment-thread"],' +
        '[role="listitem"], .message-row, .artifact-viewer {' +
        ' contain: layout style;' +
        ' }' +
        '*{ -webkit-tap-highlight-color: transparent; }' +
        // Scroll areas inside bottom sheets (Settings etc.): with the
        // overscroll "contain" from the rule above, a vertical swipe never
        // scrolls them (Appearance/General pages stay stuck at the top).
        '.aux-drawer-popup .overflow-y-auto, [data-drawer-content] .overflow-y-auto,' +
        ' [role="dialog"] .overflow-y-auto {' +
        ' overscroll-behavior-y: auto;' +
        ' }';
      (doc.head || doc.documentElement).appendChild(gpu);
    }
  } catch (e) {}
}
