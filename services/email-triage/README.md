# email-triage

Local Mac runner that triages Gmail via a local Gmail MCP server, calls
the Anthropic API directly, and writes activity to Supabase. Pairs with
the `/triage` page in `karl-command-center`.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Mac Studio                                                  │
│                                                             │
│   launchd  ──every 60s──▶  scripts/run-poll.sh              │
│                                  │                          │
│                                  ▼                          │
│                          python -m triage poll              │
│                          ┌────────────────────────┐         │
│                          │ Gmail MCP (stdio)      │         │
│                          │ Anthropic Opus 4.7     │         │
│                          │ Todoist REST           │         │
│                          │ GitHub REST            │         │
│                          │ Twilio REST            │         │
│                          └─────────┬──────────────┘         │
│                                    │                        │
└────────────────────────────────────┼────────────────────────┘
                                     │ Supabase JS / REST
                                     ▼
                          ┌──────────────────────┐
                          │ Supabase (paused-friendly)
                          │ • triage_events      │◀──── Vercel /triage page
                          │ • triage_budget      │      (read-only, server-side)
                          │ • triage_processed   │
                          └──────────────────────┘
```

## What it does

Every minute, launchd runs one poll cycle:

1. Preflight: bail if daily $ cap or daily count cap is hit.
2. Spawn the local Gmail MCP server over stdio.
3. List recent Gmail messages matching the sender allowlist.
4. For each unprocessed message:
   - Verify sender is in `SENDER_ALLOWLIST` (second-line defense).
   - Run a Claude agent loop with these tools:
     - `gmail_apply_label` (via MCP) → `triaged/<tier>`
     - `gmail_draft_reply` (via MCP) → drafts only, never sent
     - `todoist_create_task`
     - `github_create_issue`
     - `twilio_send_urgent_sms` (urgent only)
     - `finish_triage` (exactly once)
   - Charge Supabase budget atomically.
5. Stream every step to `triage_events` for the dashboard.

## Setup on the Mac

### 1. Install uv (if not already)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone & install deps

```bash
cd ~/karl-infra/services/email-triage
uv sync
```

### 3. Configure secrets via .env

```bash
cp .env.example .env
chmod 600 .env
```

Open `.env` and paste values from KeePass:

- `ANTHROPIC_API_KEY` — from KeePass
- `SUPABASE_URL` — already filled in
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase Dashboard → Project Settings → API → "service_role" secret
- `GMAIL_MCP_COMMAND` / `GMAIL_MCP_ARGS` — points at your existing Gmail MCP server
- `GITHUB_TOKEN` — PAT with `repo` scope
- `TODOIST_TOKEN` — from Todoist integrations page
- `TWILIO_*` — from Twilio console (optional; only used for urgent SMS)
- `SENDER_ALLOWLIST` — already set to your two emails

### 4. Smoke test

```bash
# Check config loads and tables are reachable:
uv run python -m triage status

# Run one poll cycle manually:
uv run python -m triage poll
```

Watch output. Send yourself a test email from `karlmarx9193@gmail.com`,
then run `triage poll` again — you should see it labeled in Gmail and a
new event row in Supabase.

### 5. Install launchd job

```bash
# Edit paths in the plist first if your repo lives somewhere other than ~/karl-infra
cp launchd/fyi.93.triage.plist ~/Library/LaunchAgents/fyi.93.triage.plist
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/fyi.93.triage.plist
launchctl enable gui/$UID/fyi.93.triage
```

Tail logs:

```bash
tail -f ~/Library/Logs/triage.log ~/Library/Logs/triage.err
```

Disable temporarily:

```bash
launchctl bootout gui/$UID/fyi.93.triage
```

## Guardrails (cost protection)

| Guard | Default | Override |
|---|---|---|
| Sender allowlist (hard) | your two emails | `SENDER_ALLOWLIST` |
| Daily $ cap | $1.00 | `DAILY_BUDGET_USD` |
| Daily triage count cap | 50 | `MAX_TRIAGES_PER_DAY` |
| Per-triage token cap | 12000 | `MAX_TOKENS_PER_TRIAGE` |
| Per-triage iteration cap | 6 | `MAX_ITERATIONS` |
| Drafts only, no auto-send | hard-coded | — |
| Pause Supabase project | optional | pauses the dashboard reads + writes |

When any cap trips, the runner logs a `budget.exceeded` event and stops.
Budget state resets at UTC midnight.

## Cost estimate (Opus 4.7, demo profile)

| Per triage | Tokens | $ |
|---|---|---|
| Cached system + tools | ~1500 read | $0.0023 |
| Fresh email input | ~600 | $0.009 |
| Output (tool calls + summary) | ~400 | $0.030 |
| **Per triage** | | **~$0.04** |

At 5 triages/day (demo): **~$0.20/day, ~$6/month**.
At the $1/day cap: max 25 triages/day on Opus.

To halve cost, set `TRIAGE_MODEL=claude-sonnet-4-6` (Sonnet 4.6) — nearly
identical quality on bounded triage tasks.

## Files

```
email-triage/
├── .env.example          # config template
├── pyproject.toml        # uv project
├── README.md             # this
├── launchd/
│   └── fyi.93.triage.plist
├── scripts/
│   └── run-poll.sh       # launchd entry point
└── triage/
    ├── __main__.py       # CLI: triage poll | triage status
    ├── config.py         # env loading
    ├── supabase_store.py # events, budget, dedupe
    ├── guardrails.py     # allowlist + preflight
    ├── gmail_mcp.py      # MCP client wrapper (Python `mcp` SDK)
    ├── tools.py          # Anthropic tool schemas + dispatch
    ├── agent.py          # Anthropic agent loop
    ├── poll.py           # poll cycle orchestration
    └── adapters/
        ├── github.py
        ├── todoist.py
        └── twilio.py
```
