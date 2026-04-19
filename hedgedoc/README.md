# HedgeDoc — Collaborative Writing

Real-time collaborative markdown editing for the writing-room.

## Quick Start

```bash
cd hedgedoc/
docker compose up -d       # Start HedgeDoc on localhost:3001
python3 sync.py push       # Push all .md files to HedgeDoc
python3 sync.py list       # See URLs for all notes
python3 sync.py watch      # Auto-push on file changes
```

## How It Works

HedgeDoc stores notes in a database, not as files. The sync bridge maps
file paths to stable note IDs using a hash of the relative path.

**Workflow:**
1. `sync.py push` — uploads your .md files to HedgeDoc as notes
2. Edit collaboratively in the browser at `localhost:3001`
3. `sync.py pull` — downloads edited notes back to .md files
4. `git add -A && git commit` — as usual

**Auto-sync:** Run `sync.py watch` in a terminal to auto-push file changes
to HedgeDoc. To auto-pull, you'd need to poll — but manual pull is usually
fine since you know when you're done editing.

## Configuration

Set environment variables to override defaults:
- `HEDGEDOC_URL` — default: `http://localhost:3001`
- `WRITING_ROOM` — default: `/home/maple/writing-room`

## Note URLs

Each .md file gets a deterministic URL like:
```
http://localhost:3001/wr-a1b2c3d4e5f6
```

Run `python3 sync.py list` to see all mappings.

## Sharing

For remote collaboration, expose port 3001 via:
- Tailscale Funnel
- Cloudflare Tunnel
- SSH port forwarding: `ssh -L 3001:localhost:3001 your-server`
