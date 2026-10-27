/**
 * patches/dm_home/state.js - small helpers.
 */
function hashName(s) {
  var h = 0;
  for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function rowStatus(row) {
  if (row.querySelector('[data-testid="status-loading-spinner"]')) return 'running';
  if (row.querySelector('.animate-ping')) return 'waiting';
  if (row.querySelector('[data-testid="status-unread-dot"]')) return 'new';
  return 'done';
}

function el(tag, cls, html) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
