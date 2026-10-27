/**
 * patches/agent_panel/install.js - mount the launcher once on <body>.
 *
 * The button lives on <body>, outside #root, so the host app's React
 * re-renders never remove it and no observer is needed.
 */
function install() {
  if (!document.body) return;
  buildFab();
}
