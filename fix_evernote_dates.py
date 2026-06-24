#!/usr/bin/env python3
"""
Parse Evernote .enex files and patch created_at on matching Clippery notes.

- Unique title match  → patch created_at
- Duplicate titles    → skip (can't safely determine which note is which)
- No match            → skip (note is from another app)

Run from Mac: python3 fix_evernote_dates.py
Set DRY_RUN = True to preview without making changes.
"""
import os, json, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone

ENEX_DIR = os.path.join(
    os.path.expanduser("~"),
    "Library/CloudStorage/SeaDrive-SetuKathawate(files.setugk.com)/My Libraries",
    "Setu's Personal Library/2. Work Related/Projects/clippery/From other apps/Evernote ENEX",
)
API_BASE = "http://10.0.0.10:5050"
DRY_RUN  = False  # set True to preview without changes


def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(
        f"{API_BASE}{path}", data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def parse_enex_date(s):
    """Convert '20210507T210738Z' → '2021-05-07T21:07:38+00:00'"""
    dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def load_enex_dates():
    """Returns dict: lowercase_title → list of ISO created_at strings"""
    dates = defaultdict(list)
    for fname in sorted(os.listdir(ENEX_DIR)):
        if not fname.endswith(".enex"):
            continue
        root = ET.parse(os.path.join(ENEX_DIR, fname)).getroot()
        for note in root.findall("note"):
            title   = (note.findtext("title") or "").strip()
            created = (note.findtext("created") or "").strip()
            if title and created:
                try:
                    dates[title.lower()].append(parse_enex_date(created))
                except ValueError:
                    pass
    return dates


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Loading ENEX dates...")
    enex = load_enex_dates()

    unique   = {t: v[0] for t, v in enex.items() if len(v) == 1}
    ambiguous = {t: v    for t, v in enex.items() if len(v) >  1}
    print(f"  {sum(len(v) for v in enex.values())} ENEX notes | {len(unique)} unique titles | {len(ambiguous)} ambiguous titles")

    print("Loading Clippery notes from API...")
    notes = api("GET", "/api/notes")
    print(f"  {len(notes)} notes in Clippery")

    stats = {"patched": 0, "skipped_ambiguous": 0, "no_match": 0, "errors": 0}

    for note in notes:
        title_key = (note.get("title") or "").strip().lower()

        if title_key in ambiguous:
            stats["skipped_ambiguous"] += 1
            continue

        if title_key not in unique:
            stats["no_match"] += 1
            continue

        new_date = unique[title_key]
        current  = note.get("created_at", "")

        if DRY_RUN:
            print(f"  DRY  {note['title'][:55]}")
            print(f"       {current[:10]} → {new_date[:10]}")
            stats["patched"] += 1
            continue

        try:
            api("PUT", f"/api/notes/{note['id']}", {"created_at": new_date})
            print(f"  OK   {note['title'][:55]}  ({current[:10]} → {new_date[:10]})")
            stats["patched"] += 1
        except Exception as e:
            print(f"  FAIL {note['title'][:55]}: {e}")
            stats["errors"] += 1

    print(f"\n{'=' * 60}")
    label = "Would patch" if DRY_RUN else "Patched"
    print(f"{label}: {stats['patched']} | Ambiguous (skipped): {stats['skipped_ambiguous']} | No ENEX match: {stats['no_match']} | Errors: {stats['errors']}")

    if ambiguous:
        print(f"\nAmbiguous titles (skipped — multiple ENEX notes with same name):")
        for t, dates in sorted(ambiguous.items()):
            print(f"  {len(dates)}x  {t[:60]}")

    if DRY_RUN:
        print("\nSet DRY_RUN = False to run for real.")


if __name__ == "__main__":
    main()
