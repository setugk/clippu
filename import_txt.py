#!/usr/bin/env python3
"""
Bear/Evernote/Journaling .txt → Clippery import.
Run from Mac on local network: python3 import_txt.py

File format expected:
  # Title
  ...body...
  #Folder/SubFolder/keyword# #Folder/keyword2#

Folder mapping:
  Path segments that start with an uppercase letter → nested Clippery folders
  All-lowercase segments                            → Clippery tags

Dedup: skips notes where BOTH title AND body content match an existing note.
Same title, different content = different note, will be imported.
"""
import os, re, json, hashlib, urllib.request, urllib.error

IMPORT_ROOT = os.path.join(
    os.path.expanduser("~"),
    "Library/CloudStorage/SeaDrive-SetuKathawate(files.setugk.com)/My Libraries",
    "Setu's Personal Library/2. Work Related/Projects/clippery/From other apps",
)
IMPORT_DIRS = ["Career Growth", "Evernote Archive", "Journaling"]
API_BASE    = "http://10.0.0.10:5050"
DRY_RUN     = False  # set True to preview without importing


# ── API helpers ───────────────────────────────────────────────────────────────

def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(
        f"{API_BASE}{path}", data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# ── Dedup ─────────────────────────────────────────────────────────────────────

def content_key(text):
    """
    Stable hash for dedup. Strips HTML (in case existing note was edited
    in the contenteditable editor and saved with <br> tags), normalises
    whitespace and lowercases before hashing.
    """
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.md5(text.encode()).hexdigest()


# ── Tag-path parsing ──────────────────────────────────────────────────────────

def normalize_tag(s):
    s = s.strip().lower()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9\-']", "", s)
    return s.strip("-")


def is_tag_segment(s):
    """
    All-lowercase (possibly hyphenated) → content keyword → Clippery tag.
    Anything with an uppercase letter → organisational category → Clippery folder.
    Examples:  "depression" → tag | "Daily journaling" → folder
    """
    return s == s.lower()


def parse_tag_line(tag_line):
    """
    Returns (folder_segments, tags) from a line like:
      #Journaling/Setu's notebook/depression# #Journaling/Setu's notebook/selfhelp#
    - folder_segments: list of folder names from the primary path (non-lowercase segs)
    - tags: all lowercase leaf segments across all paths
    """
    paths = re.findall(r"#([^#]+)#", tag_line)
    folder_segments = []
    tags = []

    for i, path in enumerate(paths):
        segments = [s.strip() for s in path.split("/") if s.strip()]
        seg_folders = [s for s in segments if not is_tag_segment(s)]
        seg_tags    = [normalize_tag(s) for s in segments if is_tag_segment(s)]

        if i == 0:
            folder_segments = seg_folders   # primary path drives folder placement
        tags.extend(seg_tags)

    # Deduplicate tags while preserving order
    seen = set()
    unique_tags = []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            unique_tags.append(t)

    return folder_segments, unique_tags


# ── File parsing ──────────────────────────────────────────────────────────────

# Matches a line that is entirely one or more #...# tag groups
TAG_LINE_RE = re.compile(r"^(#[^#\n]+#\s*)+$")


def parse_file(filepath):
    """
    Returns (title, body, tag_paths_line) or raises on error.
    Handles the trailing `#tag#` line(s) and the `# Title` first line.
    """
    with open(filepath, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    lines = raw.splitlines()
    if not lines:
        return "", "", ""

    # Title from first line
    title = lines[0].lstrip("#").strip() if lines else ""

    # Walk up from the end to find the tag line(s)
    end_body = len(lines)
    for i in range(len(lines) - 1, 0, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if TAG_LINE_RE.match(stripped):
            end_body = i
        else:
            break

    body     = "\n".join(lines[1:end_body]).strip()
    tag_line = "\n".join(lines[end_body:]).strip()

    return title, body, tag_line


# ── Folder cache ──────────────────────────────────────────────────────────────

def get_or_create_folder(folder_names, existing_folders, folder_cache, dry_run):
    """
    Walks the folder_names list, creating missing folders as needed.
    Returns the deepest folder's ID (or None if folder_names is empty).
    folder_cache key: (lowercase_name, parent_id)
    """
    parent_id = None
    for name in folder_names:
        key = (name.lower(), parent_id)
        if key in folder_cache:
            parent_id = folder_cache[key]
            continue

        # Check existing folders
        found = next(
            (f for f in existing_folders
             if f["name"].lower() == name.lower() and f.get("parent_id") == parent_id),
            None
        )
        if found:
            folder_cache[key] = found["id"]
            parent_id = found["id"]
        else:
            if dry_run:
                fake_id = f"dry-{name.lower()[:8]}-{parent_id}"
                folder_cache[key] = fake_id
                existing_folders.append({"id": fake_id, "name": name, "parent_id": parent_id})
                parent_id = fake_id
                print(f"    [DRY] Would create folder: {name!r} (parent: {parent_id})")
            else:
                new_f = api("POST", "/api/folders", {"name": name, "parent_id": parent_id})
                existing_folders.append(new_f)
                folder_cache[key] = new_f["id"]
                parent_id = new_f["id"]
                print(f"    Created folder: {name!r}")

    return parent_id


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Loading existing data from Clippery...")

    existing_notes   = api("GET", "/api/notes")
    existing_folders = api("GET", "/api/folders")

    # Dedup set: (lowercase_title, content_hash)
    existing_keys = {
        (n["title"].strip().lower(), content_key(n.get("body", "")))
        for n in existing_notes
    }
    print(f"  {len(existing_notes)} existing notes | {len(existing_folders)} existing folders")

    folder_cache = {}   # (lowercase_name, parent_id) → folder_id
    stats = {"imported": 0, "skipped_dup": 0, "skipped_empty": 0, "errors": 0}

    for dirname in IMPORT_DIRS:
        dirpath = os.path.join(IMPORT_ROOT, dirname)
        print(f"\n── {dirname} ({'DRY' if DRY_RUN else 'LIVE'}) ──")

        try:
            filenames = sorted(f for f in os.listdir(dirpath) if f.endswith(".txt"))
        except FileNotFoundError:
            print(f"  Directory not found: {dirpath}")
            continue

        for filename in filenames:
            # Skip exact-duplicate export artifacts (File (1).txt)
            if re.search(r"\(\d+\)\.txt$", filename):
                continue

            filepath = os.path.join(dirpath, filename)

            try:
                title, body, tag_line = parse_file(filepath)
            except Exception as e:
                print(f"  ERROR parsing {filename}: {e}")
                stats["errors"] += 1
                continue

            if not title:
                stats["skipped_empty"] += 1
                continue

            # Dedup: same title AND same content → true duplicate, skip
            key = (title.strip().lower(), content_key(body))
            if key in existing_keys:
                print(f"  DUP  {title[:65]}")
                stats["skipped_dup"] += 1
                continue

            folder_segments, tags = parse_tag_line(tag_line)
            folder_id = get_or_create_folder(
                folder_segments, existing_folders, folder_cache, DRY_RUN
            )

            folder_path = " > ".join(folder_segments) if folder_segments else "(root)"
            tag_display = ", ".join(f"#{t}" for t in tags) if tags else "no tags"

            if DRY_RUN:
                print(f"  DRY  {title[:55]}")
                print(f"       folder: {folder_path} | tags: {tag_display}")
                stats["imported"] += 1
                existing_keys.add(key)  # prevent counting same note twice in dry run
                continue

            try:
                api("POST", "/api/notes", {
                    "title": title,
                    "body": body,
                    "folder_id": folder_id,
                    "tags": tags,
                })
                existing_keys.add(key)
                print(f"  OK   {title[:65]}")
                stats["imported"] += 1
            except Exception as e:
                print(f"  FAIL {title[:55]}: {e}")
                stats["errors"] += 1

    print(f"\n{'=' * 60}")
    label = "Would import" if DRY_RUN else "Imported"
    print(f"{label}: {stats['imported']} | Skipped (dup): {stats['skipped_dup']} | Errors: {stats['errors']}")
    if DRY_RUN:
        print("Set DRY_RUN = False to run for real.")


if __name__ == "__main__":
    main()
