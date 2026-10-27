/**
 * patches/dm_settings/state.js - host state used by the summaries and toggles.
 */
function isDark() {
  try {
    var b = document.body;
    if (b && (b.classList.contains('dark') || b.classList.contains('theme-dark'))) return true;
    if (b && b.classList.contains('theme-light')) return false;
    return document.documentElement.classList.contains('dark');
  } catch (_) { return true; }
}

function hasAutoResume() {
  return !!(window.Android && typeof window.Android.isAutoResumeEnabled === 'function');
}

function autoResumeOn() {
  try { return hasAutoResume() ? !!window.Android.isAutoResumeEnabled() : true; } catch (_) { return true; }
}

function setAutoResume(on) {
  try {
    if (window.Android && typeof window.Android.setAutoResumeEnabled === 'function') {
      window.Android.setAutoResumeEnabled(window.__AG_NATIVE_BRIDGE_TOKEN__, !!on);
    }
  } catch (_) {}
}
