# Gmail Noise Sweep

**Status: LIVE 2026-06-06** · hourly LaunchAgent on the Mac Studio

Labels and archives recurring inbox noise in `karlmarx9193@gmail.com`:

| Category | Label | Rule |
|----------|-------|------|
| Auto-forwarded SMS | `SMS` | from self + subject `"SMS from"` |
| Marketing senders | `Noise/Promos` | curated sender list (~28 senders) |
| Dev/political newsletters | `Noise/Newsletters` | curated sender list (6 senders) |

Initial backfill on 2026-06-06 cleaned **846 inbox threads** (227 SMS, 523
promos, 96 newsletters). Starred (`\Flagged`) messages are always skipped.
Archived mail keeps its label and stays in All Mail — recover any sender by
searching the label and re-adding to inbox.

## Components

- **Script**: `~/karl-infra/scripts/gmail_noise_sweep.py` (stdlib-only, `uv run`)
  - Sender lists live at the top of the script — edit there to add/remove noise.
  - `--dry-run` prints what would be cleaned without touching anything.
- **LaunchAgent**: `~/Library/LaunchAgents/com.karlmarx.gmail-noise-sweep.plist`
  (label `com.karlmarx.gmail-noise-sweep`, StartInterval 3600)
- **Logs**: `~/.local/share/gmail-noise-sweep/sweep.log`
- **Credentials**: reuses `GMAIL_USER` / `GMAIL_APP_PASSWORD` from
  `~/karl-infra/services/email-triage/.env` (IMAP app password)

## How it writes (important)

The claude.ai Gmail MCP connector is **read + drafts only** (no
`gmail.modify` / `gmail.labels` scopes — label/archive calls return
"insufficient authentication scopes"). The write path is **Gmail IMAP**:

- `CREATE "<name>"` → real Gmail label (nested via `/`)
- `UID STORE +X-GM-LABELS ("<name>")` → apply label
- `+FLAGS (\Seen \Deleted)` + `EXPUNGE` while INBOX is selected → archive
  (removes only the INBOX label; message remains in All Mail)

## Native Gmail filters (preferred long-term)

`~/karl-infra/scripts/gmail-noise-filters.xml` (copy in `~/Downloads/`)
mirrors the same rules as importable Gmail filters:
Gmail → Settings → Filters and Blocked Addresses → Import filters.
Once imported, Gmail applies the rules server-side at delivery time and the
LaunchAgent becomes redundant (safe to keep as backstop, or
`launchctl unload` it).

## Cross-refs

- `infra/cld-email.md` — separate cld@93.fyi triage system
- `services/email-triage/` — LLM triage poller (allowlisted senders only)
