import sqlite3
import os
import uuid
from datetime import datetime, timezone

DB_PATH = "/data/clippery.db"


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


_SCHEMA_VERSION = 1


def init_db():
    conn = get_conn()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            )
        """)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        current = int(row["version"]) if row else 0

        if current < 1:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_id TEXT REFERENCES folders(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    body TEXT NOT NULL DEFAULT '',
                    folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tags (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS note_tags (
                    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                    tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (note_id, tag_id)
                );
                CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id);
                CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);
            """)
            if current == 0:
                conn.execute("INSERT INTO schema_version VALUES (1)")
            else:
                conn.execute("UPDATE schema_version SET version = 1")

        # ── Add future migrations here ────────────────────────────────────────
        # if current < 2:
        #     conn.execute("ALTER TABLE notes ADD COLUMN starred INTEGER DEFAULT 0")
        #     conn.execute("UPDATE schema_version SET version = 2")

    conn.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


# ── Folders ──────────────────────────────────────────────────────────────────

def get_folders():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM folders ORDER BY name COLLATE NOCASE").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_folder(name, parent_id=None):
    conn = get_conn()
    folder = {"id": new_id(), "name": name, "parent_id": parent_id,
              "created_at": now(), "updated_at": now()}
    with conn:
        conn.execute(
            "INSERT INTO folders VALUES (:id,:name,:parent_id,:created_at,:updated_at)",
            folder
        )
    conn.close()
    return folder


def rename_folder(folder_id, name):
    conn = get_conn()
    ts = now()
    with conn:
        conn.execute("UPDATE folders SET name=?, updated_at=? WHERE id=?", (name, ts, folder_id))
    row = conn.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_folder(folder_id):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
    conn.close()


# ── Notes ─────────────────────────────────────────────────────────────────────

def _note_tags(conn, note_id):
    rows = conn.execute(
        "SELECT t.name FROM tags t JOIN note_tags nt ON t.id=nt.tag_id WHERE nt.note_id=? ORDER BY t.name",
        (note_id,)
    ).fetchall()
    return [r["name"] for r in rows]


def get_notes(folder_id=None, tag=None, query=None):
    conn = get_conn()
    sql = "SELECT DISTINCT n.* FROM notes n"
    params = []
    joins, wheres = [], []

    if tag:
        joins.append("JOIN note_tags nt ON n.id=nt.note_id JOIN tags t ON nt.tag_id=t.id")
        wheres.append("t.name=?")
        params.append(tag)

    if folder_id == "root":
        wheres.append("n.folder_id IS NULL")
    elif folder_id:
        wheres.append("n.folder_id=?")
        params.append(folder_id)

    if query:
        wheres.append("(n.title LIKE ? OR n.body LIKE ?)")
        q = f"%{query}%"
        params += [q, q]

    if joins:
        sql += " " + " ".join(joins)
    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY n.updated_at DESC"

    rows = conn.execute(sql, params).fetchall()
    notes = []
    for row in rows:
        n = dict(row)
        n["tags"] = _note_tags(conn, n["id"])
        notes.append(n)
    conn.close()
    return notes


def get_note(note_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not row:
        conn.close()
        return None
    n = dict(row)
    n["tags"] = _note_tags(conn, note_id)
    conn.close()
    return n


def create_note(title="", body="", folder_id=None, created_at=None, tags=None):
    conn = get_conn()
    ts = now()
    nid = new_id()
    note = {"id": nid, "title": title, "body": body,
            "folder_id": folder_id, "created_at": created_at or ts, "updated_at": ts}
    with conn:
        conn.execute(
            "INSERT INTO notes VALUES (:id,:title,:body,:folder_id,:created_at,:updated_at)",
            note
        )
        if tags:
            for tag_name in tags:
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue
                row = conn.execute("SELECT id FROM tags WHERE name=?", (tag_name,)).fetchone()
                tag_id = row["id"] if row else new_id()
                if not row:
                    conn.execute("INSERT INTO tags VALUES (?,?)", (tag_id, tag_name))
                conn.execute("INSERT OR IGNORE INTO note_tags VALUES (?,?)", (nid, tag_id))
    note["tags"] = [t.strip().lower() for t in tags if t.strip()] if tags else []
    conn.close()
    return note


def update_note(note_id, **kwargs):
    conn = get_conn()
    sets, params = ["updated_at=?"], [now()]

    for field in ("title", "body", "folder_id"):
        if field in kwargs:
            sets.append(f"{field}=?")
            params.append(kwargs[field])

    params.append(note_id)
    with conn:
        conn.execute(f"UPDATE notes SET {','.join(sets)} WHERE id=?", params)

        if "tags" in kwargs:
            conn.execute("DELETE FROM note_tags WHERE note_id=?", (note_id,))
            for tag_name in kwargs["tags"]:
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue
                row = conn.execute("SELECT id FROM tags WHERE name=?", (tag_name,)).fetchone()
                tag_id = row["id"] if row else new_id()
                if not row:
                    conn.execute("INSERT INTO tags VALUES (?,?)", (tag_id, tag_name))
                conn.execute("INSERT OR IGNORE INTO note_tags VALUES (?,?)", (note_id, tag_id))

        conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM note_tags)")

    result = get_note(note_id)
    conn.close()
    return result


def delete_note(note_id):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.close()


def delete_tag(name):
    conn = get_conn()
    with conn:
        row = conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()
        if row:
            conn.execute("DELETE FROM note_tags WHERE tag_id=?", (row["id"],))
            conn.execute("DELETE FROM tags WHERE id=?", (row["id"],))
    conn.close()


def rename_tag(old_name, new_name):
    conn = get_conn()
    with conn:
        existing = conn.execute("SELECT id FROM tags WHERE name=?", (new_name,)).fetchone()
        old_row  = conn.execute("SELECT id FROM tags WHERE name=?", (old_name,)).fetchone()
        if not old_row:
            conn.close()
            return
        if existing:
            conn.execute("UPDATE OR IGNORE note_tags SET tag_id=? WHERE tag_id=?",
                         (existing["id"], old_row["id"]))
            conn.execute("DELETE FROM note_tags WHERE tag_id=?", (old_row["id"],))
            conn.execute("DELETE FROM tags WHERE id=?", (old_row["id"],))
        else:
            conn.execute("UPDATE tags SET name=? WHERE id=?", (new_name, old_row["id"]))
    conn.close()


# ── Tags ──────────────────────────────────────────────────────────────────────

def get_tags():
    conn = get_conn()
    rows = conn.execute(
        "SELECT t.name, COUNT(nt.note_id) as count FROM tags t "
        "LEFT JOIN note_tags nt ON t.id=nt.tag_id GROUP BY t.id ORDER BY t.name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Export ────────────────────────────────────────────────────────────────────

def export_all():
    conn = get_conn()
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    folders = [dict(r) for r in conn.execute("SELECT * FROM folders ORDER BY name COLLATE NOCASE").fetchall()]
    note_rows = conn.execute("SELECT * FROM notes ORDER BY created_at").fetchall()
    notes = []
    for row in note_rows:
        n = dict(row)
        n["tags"] = _note_tags(conn, n["id"])
        notes.append(n)
    conn.close()
    return {"schema_version": _SCHEMA_VERSION, "folders": folders, "notes": notes}


# ── Sync ──────────────────────────────────────────────────────────────────────

def get_sync_version():
    conn = get_conn()
    row = conn.execute("SELECT MAX(updated_at) as v FROM notes").fetchone()
    conn.close()
    return row["v"] or ""
