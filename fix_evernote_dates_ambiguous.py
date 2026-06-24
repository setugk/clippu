#!/usr/bin/env python3
"""
Second-pass date fix for ambiguous (duplicate-title) Evernote notes.
Matches by content similarity — strips tags, normalises whitespace, compares.

Run from Mac after fix_evernote_dates.py: python3 fix_evernote_dates_ambiguous.py
"""
import os, re, json, hashlib, urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone

ENEX_DIR = os.path.join(
    os.path.expanduser("~"),
    "Library/CloudStorage/SeaDrive-SetuKathawate(files.setugk.com)/My Libraries",
    "Setu's Personal Library/2. Work Related/Projects/clippery/From other apps/Evernote ENEX",
)
API_BASE = "http://10.0.0.10:5050"
DRY_RUN  = False


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
    dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def normalise(text):
    """Strip HTML/XML tags, collapse whitespace, lowercase."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def content_hash(text):
    return hashlib.md5(normalise(text).encode()).hexdigest()


def enml_to_text(content_el):
    """Extract plain text from an ENML <content> element (CDATA string)."""
    raw = content_el.text or ""
    # The CDATA is itself XML — parse it to get text
    try:
        inner = ET.fromstring(raw)
        return " ".join(inner.itertext())
    except ET.ParseError:
        return raw


def load_ambiguous_enex():
    """
    Returns dict: lowercase_title → list of {created_at, text_hash, text_snippet}
    Only titles with 2+ notes.
    """
    by_title = defaultdict(list)
    for fname in sorted(os.listdir(ENEX_DIR)):
        if not fname.endswith(".enex"):
            continue
        root = ET.parse(os.path.join(ENEX_DIR, fname)).getroot()
        for note in root.findall("note"):
            title   = (note.findtext("title") or "").strip()
            created = (note.findtext("created") or "").strip()
            content_el = note.find("content")
            if not (title and created and content_el is not None):
                continue
            try:
                iso = parse_enex_date(created)
            except ValueError:
                continue
            text = enml_to_text(content_el)
            by_title[title.lower()].append({
                "created_at": iso,
                "hash": content_hash(text),
                "snippet": normalise(text)[:120],
            })

    return {t: v for t, v in by_title.items() if len(v) > 1}


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Loading ambiguous ENEX notes (content matching)...")
    ambiguous = load_ambiguous_enex()
    print(f"  {len(ambiguous)} ambiguous titles covering {sum(len(v) for v in ambiguous.values())} ENEX notes")

    print("Loading Clippery notes from API...")
    all_notes = api("GET", "/api/notes")

    # Only look at Clippery notes whose title is in the ambiguous set
    candidates = [n for n in all_notes if (n.get("title") or "").strip().lower() in ambiguous]
    print(f"  {len(candidates)} Clippery notes to match")

    stats = {"patched": 0, "still_ambiguous": 0, "no_content_match": 0, "errors": 0}
    still_ambiguous = []

    for note in candidates:
        title_key  = (note.get("title") or "").strip().lower()
        enex_group = ambiguous[title_key]
        clippery_hash = content_hash(note.get("body") or "")

        # Try exact content hash match
        matches = [e for e in enex_group if e["hash"] == clippery_hash]

        if len(matches) == 1:
            new_date = matches[0]["created_at"]
            current  = note.get("created_at", "")
            if DRY_RUN:
                print(f"  DRY  {note['title'][:55]}")
                print(f"       {current[:10]} → {new_date[:10]}  (content matched)")
                stats["patched"] += 1
            else:
                try:
                    api("PUT", f"/api/notes/{note['id']}", {"created_at": new_date})
                    print(f"  OK   {note['title'][:55]}  ({current[:10]} → {new_date[:10]})")
                    stats["patched"] += 1
                except Exception as e:
                    print(f"  FAIL {note['title'][:55]}: {e}")
                    stats["errors"] += 1
        elif len(matches) > 1:
            stats["still_ambiguous"] += 1
            still_ambiguous.append(note["title"])
        else:
            stats["no_content_match"] += 1
            still_ambiguous.append(note["title"])

    print(f"\n{'=' * 60}")
    label = "Would patch" if DRY_RUN else "Patched"
    print(f"{label}: {stats['patched']} | Still ambiguous: {stats['still_ambiguous']} | No content match: {stats['no_content_match']} | Errors: {stats['errors']}")

    if still_ambiguous:
        print(f"\nNotes not resolved (manual review needed):")
        for t in sorted(set(still_ambiguous)):
            print(f"  {t}")

    if DRY_RUN:
        print("\nSet DRY_RUN = False to run for real.")


if __name__ == "__main__":
    main()
