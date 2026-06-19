import os
import json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
DATA_FILE = "/data/history.json"
SETTINGS_FILE = "/data/settings.json"
DEFAULT_MAX = int(os.environ.get("CLIPPERY_MAX", 25))

CLIPPERY_USER = os.environ.get("CLIPPERY_USER")
CLIPPERY_PASS = os.environ.get("CLIPPERY_PASS")

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if CLIPPERY_USER and CLIPPERY_PASS:
            auth = request.authorization
            if not auth or auth.username != CLIPPERY_USER or auth.password != CLIPPERY_PASS:
                return Response(
                    "Authentication required.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Clippery"'}
                )
        return f(*args, **kwargs)
    return decorated

def read_history():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_history(history):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(history, f)

def read_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"max": DEFAULT_MAX, "dark": False}

def write_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clippery</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%23111'/><text x='16' y='23' text-anchor='middle' font-family='-apple-system,sans-serif' font-weight='600' font-size='19' fill='white'>C</text></svg>">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { height: -webkit-fill-available; }

:root {
  --bg: #F5F5F5; --surface: #FFFFFF; --border: #E5E5E5; --border-mid: #D4D4D4;
  --text: #111111; --text-muted: #A3A3A3; --text-faint: #C4C4C4;
  --subtle: #FAFAFA; --subtle-2: #F5F5F5; --divider: #F0F0F0;
  --accent: #111111; --accent-fg: #FFFFFF; --disabled-bg: #EBEBEB;
}
[data-dark] {
  --bg: #0F0F0F; --surface: #1A1A1A; --border: #2A2A2A; --border-mid: #404040;
  --text: #EFEFEF; --text-muted: #636363; --text-faint: #454545;
  --subtle: #161616; --subtle-2: #222222; --divider: #232323;
  --accent: #EFEFEF; --accent-fg: #111111; --disabled-bg: #2A2A2A;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  height: 100dvh;
  min-height: -webkit-fill-available;
  display: flex;
  flex-direction: column;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  max-width: 1000px;
  margin: 0 auto;
}

/* Bar */
.bar {
  height: 48px;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  flex-shrink: 0;
  z-index: 10;
  margin: 8px 12px 0;
  border-radius: 10px;
}
.bar-title { font-size: 14px; font-weight: 600; letter-spacing: -0.02em; }
.bar-actions { margin-left: auto; display: flex; align-items: center; }

.settings-wrapper { position: relative; }
.settings-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); border-radius: 8px;
  transition: background 0.1s, color 0.1s;
}
.settings-btn:hover { background: var(--subtle-2); color: var(--text); }

.settings-dropdown {
  display: none;
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  padding: 6px;
  min-width: 170px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  z-index: 200;
}
.settings-dropdown.open { display: block; }
.settings-dropdown-label {
  font-size: 10px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.07em;
  padding: 4px 8px 6px;
}
.settings-divider { height: 1px; background: var(--border); margin: 4px 0; }
.settings-option {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 7px 10px;
  border-radius: 6px; border: none; background: none;
  font-size: 13px; font-family: inherit; color: var(--text);
  cursor: pointer; text-align: left; transition: background 0.08s;
}
.settings-option:hover { background: var(--subtle-2); }
.settings-option .opt-check { visibility: hidden; }
.settings-option.active { font-weight: 600; }
.settings-option.active .opt-check { visibility: visible; }
.settings-toggle {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 7px 10px;
  border-radius: 6px; border: none; background: none;
  font-size: 13px; font-family: inherit; color: var(--text);
  cursor: pointer; transition: background 0.08s;
}
.settings-toggle:hover { background: var(--subtle-2); }
.toggle-track {
  width: 28px; height: 16px; border-radius: 8px;
  background: var(--border-mid); position: relative;
  transition: background 0.2s; flex-shrink: 0;
}
.toggle-track.on { background: var(--accent); }
.toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 12px; height: 12px; border-radius: 50%;
  background: var(--surface); transition: transform 0.2s;
}
.toggle-track.on .toggle-thumb { transform: translateX(12px); }

/* Layout */
.main {
  flex: 1;
  overflow: hidden;
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: 1fr;
  min-height: 0;
}

/* History panel (left) */
.history-panel {
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 12px;
  margin: 12px 0 12px 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.history-header {
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--divider);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.history-label {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.07em;
}
.clear-all-btn {
  font-size: 11px; font-weight: 500; color: var(--text-faint);
  background: none; border: none; cursor: pointer;
  padding: 2px 6px; border-radius: 4px; transition: color 0.12s; letter-spacing: 0;
}
.clear-all-btn:hover { color: #DC2626; }

.history-list { flex: 1; overflow-y: auto; min-height: 0; }
.history-list::-webkit-scrollbar { width: 3px; }
.history-list::-webkit-scrollbar-track { background: transparent; }
.history-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.history-item {
  padding: 10px 14px;
  border-bottom: 1px solid var(--subtle-2);
  display: flex; align-items: flex-start; gap: 6px;
  cursor: pointer; transition: background 0.08s; user-select: none;
}
.history-item:last-child { border-bottom: none; }
.history-item:hover { background: var(--subtle); }
.history-item.selected {
  background: var(--subtle-2);
  border-left: 2px solid var(--accent);
  padding-left: 12px;
}

.item-body { flex: 1; min-width: 0; }
.item-text {
  font-size: 12.5px; line-height: 1.5; color: var(--text);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; word-break: break-word;
}
.item-time { margin-top: 3px; font-size: 10.5px; color: var(--text-faint); }

.del-btn {
  flex-shrink: 0; width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; border-radius: 4px; cursor: pointer;
  color: var(--text-faint); transition: color 0.12s, background 0.12s;
  padding: 0; margin-top: 1px;
}
.del-btn:hover { color: #DC2626; background: #FFF1F2; }

.empty-state {
  padding: 40px 16px; text-align: center;
  color: var(--text-faint); font-size: 12px; line-height: 1.8;
}

/* Compose (right) */
.compose-right {
  display: flex; flex-direction: column;
  padding: 24px 32px 12px; gap: 12px; overflow: hidden; min-height: 0;
}
.spacer { flex: 1; }

/* Preview box */
.preview-box {
  display: none; position: relative;
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: 12px; overflow: hidden; min-height: 0;
}
.preview-box.visible { display: flex; flex-direction: column; flex: 1; }

.preview-actions {
  position: absolute; top: 10px; right: 10px;
  display: flex; gap: 4px; z-index: 2;
  background: var(--surface); border-radius: 8px; padding: 2px;
  box-shadow: 0 0 0 1.5px var(--border);
}
.preview-copy-btn {
  font-size: 12px; font-weight: 500; color: var(--text);
  background: none; border: none; cursor: pointer;
  padding: 5px 10px; border-radius: 6px;
  display: flex; align-items: center; gap: 5px;
  transition: background 0.1s, color 0.12s; white-space: nowrap;
}
.preview-copy-btn:hover { background: var(--subtle-2); }
.preview-copy-btn.copied { color: #16A34A; background: #F0FDF4; }

.preview-close {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; border-radius: 6px; cursor: pointer;
  color: var(--text-muted); transition: background 0.1s, color 0.1s; padding: 0;
}
.preview-close:hover { background: var(--subtle-2); color: var(--text); }

.preview-content {
  flex: 1; min-height: 0; padding: 48px 18px 16px;
  font-size: 14px; line-height: 1.65; color: var(--text);
  white-space: pre-wrap; word-break: break-word; overflow-y: auto;
}
.preview-content::-webkit-scrollbar { width: 3px; }
.preview-content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* Input wrapper */
.input-wrapper {
  display: flex; align-items: center; gap: 8px; padding: 8px;
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: 14px; transition: border-color 0.15s; flex-shrink: 0;
}
.input-wrapper:focus-within { border-color: var(--border-mid); }

textarea {
  flex: 1; min-width: 0; min-height: 38px;
  padding: 7px 4px 7px 10px; font-size: 15px; font-family: inherit;
  line-height: 1.6; color: var(--text); background: transparent;
  border: none; resize: none; outline: none; overflow-y: hidden; height: 38px;
}
textarea::placeholder { color: var(--text-faint); }

.send-btn {
  flex-shrink: 0; width: 34px; height: 34px;
  background: var(--accent); color: var(--accent-fg);
  border: none; border-radius: 9px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: opacity 0.12s, transform 0.06s;
}
.send-btn:hover:not(:disabled) { opacity: 0.8; }
.send-btn:active:not(:disabled) { transform: scale(0.88); }
.send-btn:disabled { background: var(--disabled-bg); color: var(--text-faint); cursor: default; }

/* Mobile */
@media (max-width: 640px) {
  .bar { margin: 8px 10px 0; }
  .main { display: flex; flex-direction: column; overflow: hidden; }
  .history-panel { flex: 1; margin: 10px 10px calc(env(safe-area-inset-bottom) + 88px); min-height: 0; overflow: hidden; }
  .compose-right {
    position: fixed; bottom: 0; left: 0; right: 0;
    padding: 10px 10px max(env(safe-area-inset-bottom), 14px);
    background: var(--bg); border-top: 1px solid var(--border); gap: 8px; z-index: 50;
  }
  .spacer { display: none; }
  .preview-box.visible { max-height: 35vh; flex: none; }
  textarea { font-size: 16px; }
}
</style>
</head>
<body>

<div class="bar">
  <span class="bar-title">Clippery</span>
  <div class="bar-actions">
    <div class="settings-wrapper">
      <button class="settings-btn" id="settings-btn" title="Settings">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      </button>
      <div class="settings-dropdown" id="settings-dropdown">
        <div class="settings-dropdown-label">History limit</div>
        <button class="settings-option" data-max="25">25 clips <span class="opt-check">✓</span></button>
        <button class="settings-option" data-max="50">50 clips <span class="opt-check">✓</span></button>
        <button class="settings-option" data-max="0">Unlimited <span class="opt-check">✓</span></button>
        <div class="settings-divider"></div>
        <div class="settings-dropdown-label">Appearance</div>
        <button class="settings-toggle" id="dark-mode-toggle">
          Dark mode
          <div class="toggle-track" id="dark-toggle-track"><div class="toggle-thumb"></div></div>
        </button>
      </div>
    </div>
  </div>
</div>

<div class="main">
  <!-- History (left) -->
  <div class="history-panel">
    <div class="history-header">
      <span class="history-label">History</span>
      <button class="clear-all-btn" id="clear-all-btn">Clear all</button>
    </div>
    <div class="history-list" id="history-list"></div>
  </div>

  <!-- Compose (right) -->
  <div class="compose-right">
    <div class="spacer" id="spacer"></div>

    <div class="preview-box" id="preview-box">
      <div class="preview-actions">
        <button class="preview-copy-btn" id="preview-copy-btn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          Copy
        </button>
        <button class="preview-close" id="preview-dismiss" title="Dismiss">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="preview-content" id="preview-content"></div>
    </div>

    <div class="input-wrapper">
      <textarea id="textarea" placeholder="Paste or type anything…"></textarea>
      <button class="send-btn" id="send-btn" disabled title="Share (⌘↵)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
  </div>
</div>

<script>
let HISTORY = __HISTORY_JSON__;
let SETTINGS = __SETTINGS_JSON__;
let selectedTs = null;

const ta          = document.getElementById('textarea');
const sendBtn     = document.getElementById('send-btn');
const listEl      = document.getElementById('history-list');
const previewBox  = document.getElementById('preview-box');
const previewContent = document.getElementById('preview-content');
const previewCopyBtn = document.getElementById('preview-copy-btn');
const previewDismiss = document.getElementById('preview-dismiss');
const clearAllBtn = document.getElementById('clear-all-btn');
const spacerEl    = document.getElementById('spacer');

// SVG constants
const PLANE_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
const CHECK_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
const COPY_SVG  = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const TRASH_SVG = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>';

// Textarea auto-resize
const MAX_TA_H = window.innerHeight - 200;
const MIN_TA_H = 38;
function resizeTa() {
  ta.style.height = '0';
  const h = Math.max(Math.min(ta.scrollHeight, MAX_TA_H), MIN_TA_H);
  ta.style.height = h + 'px';
  ta.style.overflowY = ta.scrollHeight > MAX_TA_H ? 'auto' : 'hidden';
}

ta.addEventListener('input', () => {
  resizeTa();
  sendBtn.disabled = ta.value.trim().length === 0;
});

// Cmd+Enter or Ctrl+Enter to send
ta.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    if (!sendBtn.disabled) doShare();
  }
});

sendBtn.addEventListener('click', doShare);

async function doShare() {
  const text = ta.value.trim();
  if (!text) return;

  ta.value = '';
  resizeTa();
  sendBtn.disabled = true;

  // Flash checkmark on send button
  sendBtn.innerHTML = CHECK_SVG;
  setTimeout(() => { sendBtn.innerHTML = PLANE_SVG; }, 1500);

  try {
    const res = await fetch('/share', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    HISTORY = data.history;
    renderHistory();
  } catch(_) {}

  ta.focus();
}

// Delete individual item (optimistic)
async function deleteItem(ts, e) {
  e.stopPropagation();
  if (selectedTs === ts) clearPreview();
  HISTORY = HISTORY.filter(i => i.ts !== ts);
  renderHistory();
  try {
    const res = await fetch('/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ts})
    });
    const data = await res.json();
    HISTORY = data.history;
    renderHistory();
  } catch(_) {}
}

// Clear all
clearAllBtn.addEventListener('click', async () => {
  if (!HISTORY.length) return;
  if (!confirm('Clear all history?')) return;
  HISTORY = [];
  clearPreview();
  renderHistory();
  try {
    await fetch('/clear', {method: 'POST'});
  } catch(_) {}
});

// Preview box
function selectItem(ts) {
  selectedTs = ts;
  const item = HISTORY.find(i => i.ts === ts);
  if (!item) return;
  previewContent.textContent = item.text;
  previewBox.classList.add('visible');
  spacerEl.style.display = 'none';
  renderHistory();
}

function clearPreview() {
  selectedTs = null;
  previewBox.classList.remove('visible');
  spacerEl.style.display = '';
  renderHistory();
}

previewDismiss.addEventListener('click', clearPreview);

previewCopyBtn.addEventListener('click', () => {
  const item = HISTORY.find(i => i.ts === selectedTs);
  if (!item) return;
  navigator.clipboard.writeText(item.text).then(() => {
    previewCopyBtn.classList.add('copied');
    previewCopyBtn.innerHTML = CHECK_SVG + ' Copied';
    setTimeout(() => {
      previewCopyBtn.classList.remove('copied');
      previewCopyBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy';
    }, 1500);
  });
});

// Helpers
function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60) return 'just now';
  const m = Math.floor(diff / 60);
  if (m < 60) return m === 1 ? '1 min ago' : m + ' mins ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h === 1 ? '1 hour ago' : h + ' hours ago';
  const d = Math.floor(h / 24);
  return d === 1 ? 'yesterday' : d + ' days ago';
}

function renderHistory() {
  if (!HISTORY.length) {
    listEl.innerHTML = '<div class="empty-state">Nothing shared yet.<br>Type and hit ⌘↵ to share.</div>';
    return;
  }
  listEl.innerHTML = HISTORY.map(item => `
    <div class="history-item${item.ts === selectedTs ? ' selected' : ''}" onclick="selectItem('${item.ts}')">
      <div class="item-body">
        <div class="item-text">${esc(item.text)}</div>
        <div class="item-time">${timeAgo(item.ts)}</div>
      </div>
      <button class="del-btn" onclick="deleteItem('${item.ts}', event)" title="Delete">${TRASH_SVG}</button>
    </div>
  `).join('');
}

renderHistory();

// Poll for changes from other devices every 5s
function historyKey() { return HISTORY.length + ':' + (HISTORY[0]?.ts || ''); }
let lastKey = historyKey();

setInterval(async () => {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    const newKey = data.history.length + ':' + (data.history[0]?.ts || '');
    if (newKey !== lastKey) {
      lastKey = newKey;
      HISTORY = data.history;
      if (selectedTs && !HISTORY.find(i => i.ts === selectedTs)) clearPreview();
      else renderHistory();
    }
  } catch(_) {}
}, 2000);

// Settings
const settingsBtn      = document.getElementById('settings-btn');
const settingsDropdown = document.getElementById('settings-dropdown');
const darkToggleTrack  = document.getElementById('dark-toggle-track');

function applyDark(dark) {
  dark ? document.documentElement.setAttribute('data-dark', '')
       : document.documentElement.removeAttribute('data-dark');
  darkToggleTrack.classList.toggle('on', dark);
}

function updateSettingsUI() {
  const cur = SETTINGS.max;
  document.querySelectorAll('.settings-option').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.max) === cur);
  });
  applyDark(!!SETTINGS.dark);
}

settingsBtn.addEventListener('click', e => {
  e.stopPropagation();
  settingsDropdown.classList.toggle('open');
});

document.addEventListener('click', () => settingsDropdown.classList.remove('open'));
settingsDropdown.addEventListener('click', e => e.stopPropagation());

document.querySelectorAll('.settings-option').forEach(btn => {
  btn.addEventListener('click', async () => {
    const max = parseInt(btn.dataset.max);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({max})
      });
      SETTINGS = await res.json();
      updateSettingsUI();
    } catch(_) {}
  });
});

document.getElementById('dark-mode-toggle').addEventListener('click', async () => {
  try {
    const res = await fetch('/api/settings', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dark: !SETTINGS.dark})
    });
    SETTINGS = await res.json();
    applyDark(SETTINGS.dark);
  } catch(_) {}
});

updateSettingsUI();
</script>
</body>
</html>"""

@app.route("/", methods=["GET"])
@requires_auth
def index():
    history = read_history()
    history_json = json.dumps(history).replace("</", "<\\/")
    settings_json = json.dumps(read_settings())
    return PAGE.replace("__HISTORY_JSON__", history_json).replace("__SETTINGS_JSON__", settings_json)

@app.route("/api/history", methods=["GET"])
@requires_auth
def api_history():
    return jsonify({"history": read_history()})

@app.route("/share", methods=["POST"])
@requires_auth
def share():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    history = read_history()
    if text:
        history.insert(0, {"text": text, "ts": datetime.now(timezone.utc).isoformat()})
        max_h = read_settings().get("max", DEFAULT_MAX)
        if max_h > 0:
            history = history[:max_h]
        write_history(history)
    return jsonify({"history": history})

@app.route("/delete", methods=["POST"])
@requires_auth
def delete_item():
    data = request.get_json(silent=True) or {}
    ts = data.get("ts", "")
    history = [i for i in read_history() if i.get("ts") != ts]
    write_history(history)
    return jsonify({"history": history})

@app.route("/clear", methods=["POST"])
@requires_auth
def clear_history():
    write_history([])
    return jsonify({"history": []})

@app.route("/api/settings", methods=["GET"])
@requires_auth
def api_settings():
    return jsonify(read_settings())

@app.route("/api/settings", methods=["POST"])
@requires_auth
def update_settings():
    data = request.get_json(silent=True) or {}
    settings = read_settings()
    if "max" in data:
        settings["max"] = int(data["max"])
    if "dark" in data:
        settings["dark"] = bool(data["dark"])
    write_settings(settings)
    return jsonify(settings)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
