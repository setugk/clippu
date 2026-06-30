import os
import time
import json
from functools import wraps
from flask import Flask, request, jsonify, render_template, Response
import db

app = Flask(__name__)
db.init_db()

CLIPPERY_USER   = os.environ.get("CLIPPERY_USER")
CLIPPERY_PASS   = os.environ.get("CLIPPERY_PASS")
JOURNERY_NAME   = os.environ.get("JOURNERY_NAME", "")
STATIC_VERSION  = str(int(time.time()))
APP_VERSION     = "1.8.0"


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if CLIPPERY_USER and CLIPPERY_PASS:
            auth = request.authorization
            if not auth or auth.username != CLIPPERY_USER or auth.password != CLIPPERY_PASS:
                return Response(
                    "Authentication required.", 401,
                    {"WWW-Authenticate": 'Basic realm="Journery"'}
                )
        return f(*args, **kwargs)
    return decorated


@app.route("/")
@requires_auth
def index():
    return render_template("index.html", journery_name=JOURNERY_NAME, static_v=STATIC_VERSION, app_version=APP_VERSION)


# ── Folders ───────────────────────────────────────────────────────────────────

@app.route("/api/folders", methods=["GET"])
@requires_auth
def list_folders():
    return jsonify(db.get_folders())


@app.route("/api/folders", methods=["POST"])
@requires_auth
def create_folder():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    return jsonify(db.create_folder(name, data.get("parent_id") or None))


@app.route("/api/folders/<folder_id>", methods=["PUT"])
@requires_auth
def update_folder(folder_id):
    data = request.get_json(silent=True) or {}
    if "parent_id" in data:
        result = db.move_folder(folder_id, data["parent_id"] or None)
        if not result:
            return jsonify({"error": "not found"}), 404
        return jsonify(result)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    result = db.rename_folder(folder_id, name)
    if not result:
        return jsonify({"error": "not found"}), 404
    return jsonify(result)


@app.route("/api/folders/<folder_id>", methods=["DELETE"])
@requires_auth
def delete_folder(folder_id):
    db.delete_folder(folder_id)
    return jsonify({"ok": True})


# ── Notes ─────────────────────────────────────────────────────────────────────

@app.route("/api/notes", methods=["GET"])
@requires_auth
def list_notes():
    return jsonify(db.get_notes(
        folder_id=request.args.get("folder_id"),
        tag=request.args.get("tag"),
        query=request.args.get("q"),
        year=request.args.get("year"),
    ))


@app.route("/api/notes/<note_id>", methods=["GET"])
@requires_auth
def get_note(note_id):
    note = db.get_note(note_id)
    if not note:
        return jsonify({"error": "not found"}), 404
    return jsonify(note)


@app.route("/api/notes", methods=["POST"])
@requires_auth
def create_note():
    data = request.get_json(silent=True) or {}
    return jsonify(db.create_note(
        title=data.get("title", ""),
        body=data.get("body", ""),
        folder_id=data.get("folder_id") or None,
        created_at=data.get("created_at") or None,
        tags=data.get("tags") or None,
    )), 201


@app.route("/api/notes/<note_id>", methods=["PUT"])
@requires_auth
def update_note(note_id):
    data = request.get_json(silent=True) or {}
    kwargs = {k: data[k] for k in ("title", "body", "folder_id", "tags", "created_at") if k in data}
    if "folder_id" in kwargs and not kwargs["folder_id"]:
        kwargs["folder_id"] = None
    result = db.update_note(note_id, **kwargs)
    if not result:
        return jsonify({"error": "not found"}), 404
    return jsonify(result)


@app.route("/api/notes/<note_id>", methods=["DELETE"])
@requires_auth
def delete_note(note_id):
    db.delete_note(note_id)
    return jsonify({"ok": True})


# ── Trash ──────────────────────────────────────────────────────────────────────

@app.route("/api/trash", methods=["GET"])
@requires_auth
def list_trash():
    tag = request.args.get("tag")
    return jsonify(db.get_trash(tag=tag))


@app.route("/api/notes/<note_id>/restore", methods=["POST"])
@requires_auth
def restore_note(note_id):
    result = db.restore_note(note_id)
    if not result:
        return jsonify({"error": "not found"}), 404
    return jsonify(result)


@app.route("/api/trash/<note_id>", methods=["DELETE"])
@requires_auth
def permanent_delete(note_id):
    db.permanent_delete(note_id)
    return jsonify({"ok": True})


# ── Tags ──────────────────────────────────────────────────────────────────────

@app.route("/api/tags", methods=["GET"])
@requires_auth
def list_tags():
    return jsonify(db.get_tags())


@app.route("/api/tags/<tag_name>", methods=["DELETE"])
@requires_auth
def delete_tag(tag_name):
    db.delete_tag(tag_name)
    return jsonify({"ok": True})


@app.route("/api/tags/<tag_name>", methods=["PUT"])
@requires_auth
def rename_tag(tag_name):
    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip().lower()
    if not new_name:
        return jsonify({"error": "name required"}), 400
    db.rename_tag(tag_name, new_name)
    return jsonify({"ok": True})


# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/api/import", methods=["POST"])
@requires_auth
def import_backup():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "notes" not in data:
        return jsonify({"error": "invalid backup payload"}), 400
    mode = request.args.get("mode", "merge")
    try:
        result = db.import_data(data, mode=mode)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@app.route("/api/export")
@requires_auth
def export_data():
    data = db.export_all()
    data["exported_at"] = db.now()
    filename = f"journery-{data['exported_at'][:10]}.json"
    return Response(
        json.dumps(data, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Sync polling ──────────────────────────────────────────────────────────────

@app.route("/api/settings/<key>", methods=["GET"])
@requires_auth
def get_setting(key):
    value = db.get_setting(key)
    return jsonify({"value": value})


@app.route("/api/settings/<key>", methods=["PUT"])
@requires_auth
def set_setting(key):
    data = request.get_json(force=True)
    db.set_setting(key, data.get("value", ""))
    return jsonify({"ok": True})


@app.route("/api/sync")
@requires_auth
def sync():
    return jsonify({"version": db.get_sync_version()})


@app.route("/manifest.json")
def manifest():
    full_name  = f"Journery | {JOURNERY_NAME}" if JOURNERY_NAME else "Journery"
    short_name = JOURNERY_NAME if JOURNERY_NAME else "Journery"
    return jsonify({
        "name": full_name,
        "short_name": short_name,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#111111",
    })


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000)
