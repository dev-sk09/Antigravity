/**
 * patches/agent_panel/public-api.js - expose and start.
 */
window.__agAgentPanel = {
  __installed: true,
  open: openPanel,
  close: closePanel,
  base: AGENT_BASE
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', install, { once: true });
} else {
  install();
}
