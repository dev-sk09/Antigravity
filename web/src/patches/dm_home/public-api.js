/**
 * patches/dm_home/public-api.js - install and expose.
 */
if (window.__AG_DM_HOME__) return;
window.__AG_DM_HOME__ = true;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', install);
} else {
  install();
}

window.__agDmHome = { rescan: scheduleScan };
