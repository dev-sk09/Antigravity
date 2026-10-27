/**
 * patches/dm_settings/public-api.js - install and expose.
 */
if (window.__AG_DM_SETTINGS__) return;
window.__AG_DM_SETTINGS__ = true;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', install);
} else {
  install();
}

window.__agDmSettings = { rescan: scheduleScan };
