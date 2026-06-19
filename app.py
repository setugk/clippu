import os
import json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
DATA_FILE = "/data/history.json"
MAX_HISTORY = 25

CLIPPU_USER = os.environ.get("CLIPPU_USER")
CLIPPU_PASS = os.environ.get("CLIPPU_PASS")

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if CLIPPU_USER and CLIPPU_PASS:
            auth = request.authorization
            if not auth or auth.username != CLIPPU_USER or auth.password != CLIPPU_PASS:
                return Response(
                    "Authentication required.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Clippu"'}
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

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clippu</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%23111'/><text x='16' y='23' text-anchor='middle' font-family='-apple-system,sans-serif' font-weight='600' font-size='19' fill='white'>C</text></svg>">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { height: -webkit-fill-available; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #F5F5F5;
  height: 100dvh;
  min-height: -webkit-fill-available;
  display: flex;
  flex-direction: column;
  color: #111;
  -webkit-font-smoothing: antialiased;
  max-width: 1000px;
  margin: 0 auto;
}

/* Bar */
.bar {
  height: 48px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #E5E5E5;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  z-index: 10;
  margin: 8px 12px 0;
  border-radius: 10px;
}
.bar-title { font-size: 14px; font-weight: 600; letter-spacing: -0.02em; }

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
  background: #fff;
  border: 1.5px solid #E5E5E5;
  border-radius: 12px;
  margin: 12px 0 12px 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.history-header {
  padding: 12px 14px 10px;
  border-bottom: 1px solid #F0F0F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.history-label {
  font-size: 11px;
  font-weight: 600;
  color: #A3A3A3;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.clear-all-btn {
  font-size: 11px;
  font-weight: 500;
  color: #C4C4C4;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color 0.12s;
  letter-spacing: 0;
}
.clear-all-btn:hover { color: #DC2626; }

.history-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.history-list::-webkit-scrollbar { width: 3px; }
.history-list::-webkit-scrollbar-track { background: transparent; }
.history-list::-webkit-scrollbar-thumb { background: #E5E5E5; border-radius: 2px; }

.history-item {
  padding: 10px 14px;
  border-bottom: 1px solid #F5F5F5;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  cursor: pointer;
  transition: background 0.08s;
  user-select: none;
}
.history-item:last-child { border-bottom: none; }
.history-item:hover { background: #FAFAFA; }
.history-item.selected {
  background: #F5F5F5;
  border-left: 2px solid #111;
  padding-left: 12px;
}

.item-body { flex: 1; min-width: 0; }
.item-text {
  font-size: 12.5px;
  line-height: 1.5;
  color: #111;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.item-time { margin-top: 3px; font-size: 10.5px; color: #C4C4C4; }

.del-btn {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #D4D4D4;
  transition: color 0.12s, background 0.12s;
  padding: 0;
  margin-top: 1px;
}
.del-btn:hover { color: #DC2626; background: #FFF1F2; }

.empty-state {
  padding: 40px 16px;
  text-align: center;
  color: #D4D4D4;
  font-size: 12px;
  line-height: 1.8;
}

/* Compose (right) */
.compose-right {
  display: flex;
  flex-direction: column;
  padding: 24px 32px 12px;
  gap: 12px;
  overflow: hidden;
  min-height: 0;
}
.spacer { flex: 1; }

/* Preview box */
.preview-box {
  display: none;
  position: relative;
  background: #fff;
  border: 1.5px solid #E5E5E5;
  border-radius: 12px;
  overflow: hidden;
  min-height: 0;
}
.preview-box.visible { display: flex; flex-direction: column; flex: 1; }

.preview-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 4px;
  z-index: 2;
  background: #fff;
  border-radius: 8px;
  padding: 2px;
  box-shadow: 0 0 0 1.5px #E5E5E5;
}

.preview-copy-btn {
  font-size: 12px;
  font-weight: 500;
  color: #111;
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background 0.1s, color 0.12s;
  white-space: nowrap;
}
.preview-copy-btn:hover { background: #F5F5F5; }
.preview-copy-btn.copied { color: #16A34A; background: #F0FDF4; }

.preview-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #A3A3A3;
  transition: background 0.1s, color 0.1s;
  padding: 0;
}
.preview-close:hover { background: #F0F0F0; color: #111; }

.preview-content {
  flex: 1;
  min-height: 0;
  padding: 48px 18px 16px;
  font-size: 14px;
  line-height: 1.65;
  color: #111;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-y: auto;
}
.preview-content::-webkit-scrollbar { width: 3px; }
.preview-content::-webkit-scrollbar-thumb { background: #E5E5E5; border-radius: 2px; }

/* Input wrapper */
.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #fff;
  border: 1.5px solid #E5E5E5;
  border-radius: 14px;
  transition: border-color 0.15s;
  flex-shrink: 0;
}
.input-wrapper:focus-within { border-color: #C4C4C4; }

textarea {
  flex: 1;
  min-width: 0;
  min-height: 38px;
  padding: 7px 4px 7px 10px;
  font-size: 15px;
  font-family: inherit;
  line-height: 1.6;
  color: #111;
  background: transparent;
  border: none;
  resize: none;
  outline: none;
  overflow-y: hidden;
  height: 38px;
}
textarea::placeholder { color: #C4C4C4; }

.send-btn {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  background: #111;
  color: #fff;
  border: none;
  border-radius: 9px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s, transform 0.06s;
}
.send-btn:hover:not(:disabled) { background: #2a2a2a; }
.send-btn:active:not(:disabled) { transform: scale(0.88); }
.send-btn:disabled { background: #EBEBEB; color: #C4C4C4; cursor: default; }

/* Mobile */
@media (max-width: 640px) {
  .bar { margin: 8px 10px 0; }
  .main { display: flex; flex-direction: column; overflow: hidden; }
  .history-panel { flex: 1; margin: 10px 10px calc(env(safe-area-inset-bottom) + 88px); min-height: 0; overflow: hidden; }
  .compose-right {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    padding: 10px 10px max(env(safe-area-inset-bottom), 14px);
    background: #F5F5F5;
    border-top: 1px solid #E5E5E5;
    gap: 8px;
    z-index: 50;
  }
  .spacer { display: none; }
  .preview-box.visible { max-height: 35vh; flex: none; }
  textarea { font-size: 16px; }
}
</style>
</head>
<body>

<div class="bar"><span class="bar-title">Clippu</span></div>

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
</script>
</body>
</html>"""

@app.route("/", methods=["GET"])
@requires_auth
def index():
    history = read_history()
    history_json = json.dumps(history).replace("</", "<\\/")
    return PAGE.replace("__HISTORY_JSON__", history_json)

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
        history = history[:MAX_HISTORY]
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
