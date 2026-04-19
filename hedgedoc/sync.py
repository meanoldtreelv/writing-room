#!/usr/bin/env python3
"""
sync.py — Bridge between writing-room .md files and HedgeDoc notes.

Usage:
  python3 sync.py push [file ...]    # Push files to HedgeDoc (create or update)
  python3 sync.py pull [note ...]    # Pull notes from HedgeDoc to files
  python3 sync.py list               # List all synced notes
  python3 sync.py watch              # Watch for file changes and auto-push

Writes go directly to PostgreSQL (via docker exec).
Reads use HTTP /{noteId}/download.
"""

import os
import sys
import json
import time
import hashlib
import argparse
import subprocess
from pathlib import Path

HEDGEDOC_URL = os.environ.get("HEDGEDOC_URL", "http://localhost:3001")
WRITING_ROOM = os.environ.get("WRITING_ROOM", "/home/maple/writing-room")
STATE_FILE = os.path.join(WRITING_ROOM, "hedgedoc", ".sync-state.json")
DB_CONTAINER = os.environ.get("HEDGEDOC_DB_CONTAINER", "hedgedoc-database-1")
DB_USER = "hedgedoc"

# Files/dirs to skip
SKIP_DIRS = {'.git', '_archive', 'node_modules', 'css', 'hedgedoc'}
SKIP_EXTENSIONS = {'.html', '.css', '.js', '.json', '.lock', '.db', '.lorebook', '.txt'}
INCLUDE_EXTENSIONS = {'.md', '.MD'}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"notes": {}, "last_sync": None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state["last_sync"] = time.time()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def slug_from_path(file_path):
    """Generate a URL-friendly slug from a file path."""
    rel = os.path.relpath(file_path, WRITING_ROOM)
    # Convert path to slug: "A Cage Of Thorns/Story Pitch.md" -> "a-cage-of-thorns-story-pitch"
    slug = rel.lower()
    slug = slug.replace('.md', '').replace('.MD', '')
    slug = slug.replace('/', '-').replace(' ', '-')
    slug = slug.replace('_', '-')
    # Collapse multiple dashes
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')


def psql_query(query, params=None):
    """Execute a PostgreSQL query via docker exec."""
    if params:
        # Build parameterized query by replacing %s with escaped values
        for val in params:
            # Escape single quotes
            escaped = str(val).replace("'", "''")
            query = query.replace('%s', f"'{escaped}'", 1)
    
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-t", "-A", "-c", query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  DB ERROR: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def check_note_exists(slug):
    """Check if a note with this slug/alias exists."""
    result = psql_query(
        f"""SELECT shortid FROM "Notes" WHERE alias = '{slug}' LIMIT 1"""
    )
    if result:
        return result.strip()
    return None


def create_note(slug, title, content):
    """Create a new note in the database."""
    note_id = str(subprocess.run(
        ["python3", "-c", "import uuid; print(uuid.uuid4())"],
        capture_output=True, text=True
    ).stdout.strip())
    
    now = time.strftime('%Y-%m-%d %H:%M:%S%z')
    shortid = hashlib.sha256(slug.encode()).hexdigest()[:10]
    
    # Escape content for SQL
    escaped_content = content.replace("'", "''")
    escaped_title = title.replace("'", "''")
    escaped_slug = slug.replace("'", "''")
    
    psql_query(f"""
        INSERT INTO "Notes" (id, shortid, alias, title, content, permission, "createdAt", "updatedAt", "savedAt", "lastchangeAt", viewcount)
        VALUES ('{note_id}', '{shortid}', '{escaped_slug}', '{escaped_title}', 
                '{escaped_content}', 'freely', '{now}', '{now}', '{now}', '{now}', 0)
    """)
    
    return shortid


def update_note(slug, content):
    """Update an existing note's content."""
    now = time.strftime('%Y-%m-%d %H:%M:%S%z')
    escaped_content = content.replace("'", "''")
    escaped_slug = slug.replace("'", "''")
    
    psql_query(f"""
        UPDATE "Notes" 
        SET content = '{escaped_content}', "updatedAt" = '{now}', "savedAt" = '{now}', "lastchangeAt" = '{now}'
        WHERE alias = '{escaped_slug}'
    """)


def push_file(file_path, state):
    """Push a file to HedgeDoc via database."""
    rel = os.path.relpath(file_path, WRITING_ROOM)
    slug = slug_from_path(file_path)

    if not os.path.exists(file_path):
        print(f"  SKIP (not found): {rel}")
        return

    with open(file_path, 'r', errors='replace') as f:
        content = f.read()

    title = Path(file_path).stem.replace('_', ' ').replace('-', ' ')
    existing_shortid = check_note_exists(slug)

    if existing_shortid:
        update_note(slug, content)
        url = f"{HEDGEDOC_URL}/{existing_shortid}"
        state["notes"][slug] = {
            "file": rel,
            "shortid": existing_shortid,
            "last_push": time.time()
        }
        print(f"  UPDATED: {rel} -> {url}")
    else:
        shortid = create_note(slug, title, content)
        url = f"{HEDGEDOC_URL}/{shortid}"
        state["notes"][slug] = {
            "file": rel,
            "shortid": shortid,
            "created": time.time(),
            "last_push": time.time()
        }
        print(f"  CREATED: {rel} -> {url}")


def pull_note(slug, state):
    """Pull a note from HedgeDoc and write to its mapped file."""
    if slug not in state["notes"]:
        print(f"  UNKNOWN note: {slug}")
        return

    info = state["notes"][slug]
    file_path = os.path.join(WRITING_ROOM, info["file"])
    shortid = info["shortid"]

    # Use HTTP to download
    result = subprocess.run(
        ["curl", "-s", f"{HEDGEDOC_URL}/{shortid}/download"],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0 and result.stdout:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(result.stdout)
        info["last_pull"] = time.time()
        print(f"  PULLED: /{shortid} -> {info['file']}")
    else:
        print(f"  ERROR pulling {slug} (/{shortid}): empty response")


def find_markdown_files():
    """Find all markdown files in the writing-room."""
    files = []
    for root, dirs, filenames in os.walk(WRITING_ROOM):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in filenames:
            if any(f.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                full = os.path.join(root, f)
                files.append(full)
    return sorted(files)


def cmd_push(args, state):
    if args.files:
        targets = [os.path.join(WRITING_ROOM, f) for f in args.files]
    else:
        targets = find_markdown_files()

    print(f"Pushing {len(targets)} file(s) to HedgeDoc...")
    for f in targets:
        push_file(f, state)
    save_state(state)


def cmd_pull(args, state):
    if args.notes:
        targets = args.notes
    else:
        targets = list(state["notes"].keys())

    print(f"Pulling {len(targets)} note(s) from HedgeDoc...")
    for note_id in targets:
        pull_note(note_id, state)
    save_state(state)


def cmd_list(args, state):
    if not state["notes"]:
        print("No synced notes yet. Run: python3 sync.py push")
        return

    print(f"HedgeDoc URL: {HEDGEDOC_URL}")
    print(f"Synced notes: {len(state['notes'])}\n")
    for slug, info in sorted(state["notes"].items(), key=lambda x: x[1]["file"]):
        url = f"{HEDGEDOC_URL}/{info['shortid']}"
        print(f"  {info['file']}")
        print(f"    -> {url}")


def cmd_watch(args, state):
    """Watch for file changes and auto-push. Requires inotifywait or falls back to polling."""
    print(f"Watching {WRITING_ROOM} for changes...")
    print(f"HedgeDoc: {HEDGEDOC_URL}")
    print("Press Ctrl+C to stop.\n")

    try:
        # Try inotifywait
        proc = subprocess.Popen(
            ["inotifywait", "-m", "-r", "-e", "modify", "--format", "%w%f",
             "--exclude", r"\.(git|archive)", WRITING_ROOM],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True
        )
        use_inotify = True
    except FileNotFoundError:
        use_inotify = False

    if use_inotify:
        last_push = {}
        for line in proc.stdout:
            path = line.strip()
            if any(path.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                # Debounce: skip if pushed within last 2 seconds
                now = time.time()
                if path in last_push and now - last_push[path] < 2:
                    continue
                last_push[path] = now
                push_file(path, state)
                save_state(state)
    else:
        # Fallback: poll every 5 seconds
        mtimes = {}
        while True:
            for f in find_markdown_files():
                mtime = os.path.getmtime(f)
                if f not in mtimes or mtimes[f] != mtime:
                    mtimes[f] = mtime
                    if f in mtimes:  # Skip first pass
                        push_file(f, state)
                        save_state(state)
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Writing-Room <-> HedgeDoc sync")
    sub = parser.add_subparsers(dest="command")

    push_p = sub.add_parser("push", help="Push files to HedgeDoc")
    push_p.add_argument("files", nargs="*", help="Specific files to push")

    pull_p = sub.add_parser("pull", help="Pull notes from HedgeDoc")
    pull_p.add_argument("notes", nargs="*", help="Specific note IDs to pull")

    sub.add_parser("list", help="List synced notes")
    sub.add_parser("watch", help="Watch for changes and auto-push")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    state = load_state()

    if args.command == "push":
        cmd_push(args, state)
    elif args.command == "pull":
        cmd_pull(args, state)
    elif args.command == "list":
        cmd_list(args, state)
    elif args.command == "watch":
        cmd_watch(args, state)


if __name__ == "__main__":
    main()
