/**
 * patches/dm_settings/config.js - DeltaMod UI step 2: Settings home screen.
 * Decorates the upstream Settings sheet (rows found by data-testid) with
 * icons, one-line summaries, section headers, an account card, search and
 * quick toggles. Only adds attributes and our own nodes; never moves or
 * removes React-owned nodes.
 */
'use strict';

var SVG = function (d) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
    ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
};

var ICONS = {
  'General': SVG('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
  'Appearance': SVG('<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/>'),
  'Models': SVG('<path d="M12 2 3 7v10l9 5 9-5V7z"/><path d="m3 7 9 5 9-5M12 12v10"/>'),
  'Customizations': SVG('<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>'),
  'Shortcuts': SVG('<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>'),
  'Provide Feedback': SVG('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>')
};

var ICON_RETRY = SVG('<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>');
var ICON_SEARCH = SVG('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>');

// Section shown above a row (first row of each group).
var GROUP_START = { 'General': 'App', 'Models': 'Agent', 'Provide Feedback': 'Help' };

function summaryFor(name) {
  switch (name) {
    case 'General': return 'Execution, permissions' + (autoResumeOn() ? ' · Auto-resume on' : ' · Auto-resume off');
    case 'Appearance': return (isDark() ? 'Dark' : 'Light') + ' theme · colors · chat width';
    case 'Models': return 'Default model and thinking';
    case 'Customizations': return 'Rules, workflows and MCP tools';
    case 'Shortcuts': return 'Keyboard and slash shortcuts';
    case 'Provide Feedback': return 'Report a bug or share an idea';
    case 'Account': return 'Plan, usage and sign out';
  }
  return '';
}
