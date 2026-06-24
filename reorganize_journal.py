#!/usr/bin/env python3
"""
Reorganise journal folders: add year subfolders within each theme folder
that spans more than one year. Skips folders with notes from only one year.

Run from Mac: python3 reorganize_journal.py
Set DRY_RUN = True to preview without making changes.
"""
import json, urllib.request, urllib.error
from collections import defaultdict

API_BASE      = "http://10.0.0.10:5050"
JOURNAL_ROOT  = "Journaling"
DRY_RUN       = False


def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(
        f"{API_BASE}{path}", data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def get_or_create_folder(name, parent_id, existing, cache):
    key = (name.lower(), parent_id)
    if key in cache:
        return cache[key]
    found = next(
        (f for f in existing if f["name"].lower() == name.lower()
         and f.get("parent_id") == parent_id), None
    )
    if found:
        cache[key] = found["id"]
        return found["id"]
    if DRY_RUN:
        fake = f"dry-{name}-{parent_id}"
        cache[key] = fake
        existing.append({"id": fake, "name": name, "parent_id": parent_id})
        print(f"    [DRY] Would create folder: {name!r}")
        return fake
    new = api("POST", "/api/folders", {"name": name, "parent_id": parent_id})
    existing.append(new)
    cache[key] = new["id"]
    print(f"    Created folder: {name!r}")
    return new["id"]


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Loading folders and notes...")
    folders  = api("GET", "/api/folders")
    by_id    = {f["id"]: f for f in folders}
    by_name  = {}
    for f in folders:
        by_name.setdefault(f["name"].lower(), []).append(f)

    # Find Journaling root
    journal_root = next(
        (f for f in folders if f["name"].lower() == JOURNAL_ROOT.lower()
         and not f.get("parent_id")), None
    )
    if not journal_root:
        print(f"ERROR: '{JOURNAL_ROOT}' root folder not found"); return

    # Get all direct children of Journaling (the theme folders)
    theme_folders = [f for f in folders if f.get("parent_id") == journal_root["id"]]
    print(f"Theme folders: {[f['name'] for f in theme_folders]}")

    folder_cache = {}
    stats = {"moved": 0, "skipped": 0, "errors": 0}

    for theme in theme_folders:
        # Get all notes directly in this theme folder (not subfolders)
        notes = api("GET", f"/api/notes?folder_id={theme['id']}")
        if not notes:
            print(f"\n{theme['name']}: no direct notes, skipping")
            continue

        # Group by year
        by_year = defaultdict(list)
        for n in notes:
            year = n["created_at"][:4]
            by_year[year].append(n)

        if len(by_year) <= 1:
            year = list(by_year.keys())[0] if by_year else "?"
            print(f"\n{theme['name']}: {len(notes)} notes all from {year} — no year folders needed")
            stats["skipped"] += len(notes)
            continue

        print(f"\n{theme['name']}: {len(notes)} notes across {sorted(by_year.keys())}")

        for year in sorted(by_year.keys()):
            year_notes = by_year[year]
            year_folder_id = get_or_create_folder(year, theme["id"], folders, folder_cache)

            for note in year_notes:
                if DRY_RUN:
                    print(f"  DRY  [{year}] {note['title'][:60]}")
                    stats["moved"] += 1
                    continue
                try:
                    api("PUT", f"/api/notes/{note['id']}", {"folder_id": year_folder_id})
                    print(f"  OK   [{year}] {note['title'][:60]}")
                    stats["moved"] += 1
                except Exception as e:
                    print(f"  FAIL [{year}] {note['title'][:50]}: {e}")
                    stats["errors"] += 1

    print(f"\n{'=' * 60}")
    label = "Would move" if DRY_RUN else "Moved"
    print(f"{label}: {stats['moved']} | Left in place: {stats['skipped']} | Errors: {stats['errors']}")
    if DRY_RUN:
        print("Set DRY_RUN = False to run for real.")


if __name__ == "__main__":
    main()
