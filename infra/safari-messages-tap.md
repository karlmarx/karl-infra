# safari-messages-tap

## Purpose

Give Claude rolling context on Karl's Google Messages thread with mom by
periodically reading the live Safari tab and appending new messages to a
JSONL archive.

The transcript is the single most useful input for the mom.93.fyi UX work
(see `~/code/mom-93fyi/`) — it's the source of truth on what mom actually
asks, what confuses her, and how often. Without it, UX decisions are
guesses.

## Components

- `~/karl-infra/services/safari-messages-tap.py` — one-shot CLI: reads the
  front Safari tab, verifies it's the expected mom thread, extracts the
  visible messages via the `mws-message-wrapper` Angular components, dedups
  by `msg-id`, appends to JSONL.
- `~/.claude/messages-context/mom.jsonl` — append-only archive,
  mode 600, one JSON object per line: `{id, dir: "in"|"out", text}`.

## Data flow

```
Mom's Android phone
    └─ Google Messages app (paired)
        └─ messages.google.com web client (Safari, paired session)
            └─ DOM (Angular `mws-message-wrapper` elements)
                └─ osascript "do JavaScript in front document"
                    └─ safari-messages-tap.py (extract + dedup)
                        └─ ~/.claude/messages-context/mom.jsonl
                            └─ Future Claude sessions (read-only)
```

## Dependencies

- Safari paired with mom's Android phone via `messages.google.com` web
  pairing (a pairing per Safari profile; QR-scanned on the phone)
- Safari Develop menu's "Allow JavaScript from Apple Events" enabled
- Python 3 (no third-party deps)

## Operational modes

- **On demand** (current): run the script manually before a Claude
  session that needs context. Mom's thread must be the front Safari tab.
- **Scheduled** (not yet wired): a launchd plist polling every 5–15 min,
  silently no-op'ing when Safari is on a different tab. Not installed
  until Karl confirms — adds a system-level persistent agent that touches
  user-private data.

## Privacy

- Archive is mode 600 in Karl's `~/.claude/` directory.
- Scope is hardcoded to mom's thread URL prefix; other threads are
  ignored even if the script runs against them.
- Not synced to Nextcloud (private to this Mac).
- No network egress — all reads are local AppleScript.

## Cross-refs

- `~/code/mom-93fyi/` — the website this context informs.
- `~/.claude/CLAUDE.md` — global instructions; Cloudflare zone & Vercel
  setup for the parent project live there.
