/**
 * patches/web_optimizations/public-api.js - install and expose.
 */
var global = window;

if (global.__AG_WEB_OPTIMIZATIONS__) return;
global.__AG_WEB_OPTIMIZATIONS__ = true;

var doc = global.document;
if (!doc) return;

installTaps(doc);
installGpu(doc);
installSheetScroll(doc);
// Logs a full ancestor dump on every swipe; dev builds only.
if (global.__APP_CONFIG__ && global.__APP_CONFIG__.devMode) {
  installScrollDebug(global, doc);
}

global.__agWebOptimizations = { installed: true };
