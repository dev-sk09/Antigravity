/**
 * patches/dm_home/config.js - DeltaMod UI step 3: Home ("Sakib Ai Agent" design).
 * Home shows a welcome screen with quick-start cards; the task list moves into
 * a side drawer opened from the menu button (with task search). Only adds
 * attributes and our own nodes; never moves or removes React-owned nodes.
 */
'use strict';

var SVG = function (d) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
    ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
};

var ICON_SEARCH = SVG('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>');
var ICON_CLEAR = SVG('<path d="M18 6 6 18M6 6l12 12"/>');
var ICON_MENU = SVG('<path d="M4 7h16M7 12h10M10 17h4"/>');

var BRAND = 'Sakib Ai Agent';

// "SA" mark: blue S tile with a frosted A tile on top.
var LOGO =
  '<svg viewBox="0 0 64 64" aria-hidden="true">' +
  '<defs><linearGradient id="dmS" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3fd0ff"/><stop offset="1" stop-color="#3a6cf0"/></linearGradient>' +
  '<linearGradient id="dmA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b7cff"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>' +
  '<rect x="2" y="2" width="38" height="38" rx="11" fill="url(#dmS)"/>' +
  '<text x="21" y="31" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="27" fill="#fff">S</text>' +
  '<rect x="22" y="22" width="40" height="40" rx="11" fill="#eef2ff" fill-opacity=".92" stroke="#fff" stroke-opacity=".8"/>' +
  '<text x="42" y="54" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="30" fill="url(#dmA)">A</text>' +
  '</svg>';

// Quick-start cards: text goes into the message box.
var CARDS = [
  { t: 'Analyze data', s: 'Charts from a CSV', c: '#14b8c4', p: 'Analyze this CSV and make charts: ',
    i: SVG('<path d="M4 19V5M4 19h16"/><path d="m7 15 4-4 3 3 5-6"/>') },
  { t: 'Decompile APK', s: 'Source & resources', c: '#f59e0b', p: 'Decompile this APK and show its source and resources: ',
    i: SVG('<path d="M12 3 3 8l9 5 9-5z"/><path d="m3 8v8l9 5 9-5V8"/>') },
  { t: 'Fix code', s: 'Find and fix bugs', c: '#8b5cf6', p: 'Find and fix the bugs in ',
    i: SVG('<path d="m8 8-5 4 5 4M16 8l5 4-5 4"/>') },
  { t: 'Browse the web', s: 'Research any topic', c: '#ec4899', p: 'Research this on the web: ',
    i: SVG('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>') }
];

// Folder colors, picked per project name so a project keeps its color.
var FOLDER_COLORS = ['#4f8cff', '#f08c3c', '#a06bff', '#2fb99a', '#ec5b8f', '#d9a520'];

var SEL_LIST = '[data-testid="conversation-list-sidebar"]';
var SEL_ROW = '[data-testid="conversation-row-sidebar"]';
var SEL_SETTINGS = '[data-testid="mobile-open-settings"]';
var SEL_INPUT = '#antigravity\\.agentSidePanelInputBox [contenteditable="true"]';
