# FinFlow

Local-first personal finance aggregator. Pulls transactions from any Teller-supported institution, stores them in DuckDB on the local machine, exposes a FastAPI REST layer for queries and Polars-powered analytics.

## Purpose

Replace the previous Plaid integration (and any third-party "personal finance dashboard" SaaS) with a zero-cost, no-cloud-database stack. Every byte of bank data stays on disk; the only outbound traffic is mutual-TLS to `api.teller.io`.

## Stack

| Layer | Tech |
|-------|------|
| Runtime | Python 3.14 via `uv` |
| Web | FastAPI + uvicorn (ORJSON responses) |
| Storage | DuckDB embedded (default `finflow.duckdb`) |
| Analytics | Polars |
| Models | Pydantic v2 + pydantic-settings |
| HTTP | httpx (async, mTLS via cert + key files) |
| Frontend | Plain HTML/JS, served by FastAPI `StaticFiles` from `frontend/` |
| Banking | Teller (5,000+ institutions, free tier, certificate auth) |

## How it runs

Two modes:

### Interactive (manual web UI)

```bash
cd ~/finflow
uv sync
uv run uvicorn finflow.main:app --reload   # or `uv run finflow` (project script)
```

Open http://localhost:8000 — the static `frontend/index.html` hosts the Teller Connect widget. Auto-generated OpenAPI docs at `/docs`. Used for first-time enrollment (Teller Connect needs a browser) and ad-hoc query work.

### Hourly background sync (LaunchAgent, staged 2026-05-09)

`com.karlmarx.finflow-sync` calls `python -m finflow.tasks.teller_pull` once per hour. The task imports `finflow.api.teller`'s sync logic in-process — no uvicorn boot, no HTTP loopback. For each row in `enrollments` it fetches `/accounts` then `/accounts/<id>/transactions?count=500` and upserts the results into `transactions` (DuckDB ON CONFLICT). Idempotent: re-runs are cheap.

| Path | Purpose |
|------|---------|
| `~/Library/LaunchAgents/com.karlmarx.finflow-sync.plist` | LaunchAgent definition (StartInterval 3600, RunAtLoad false, ThrottleInterval 3600) |
| `~/finflow/finflow/tasks/teller_pull.py` | One-shot entrypoint — `python -m finflow.tasks.teller_pull` |
| `~/.local/share/finflow-sync/stdout.log` | Per-run log (single-line ISO timestamps, INFO level) |
| `~/.local/share/finflow-sync/stderr.log` | Tracebacks + uv noise |

Activation (manual — Karl loads, not the assistant):

```bash
launchctl load ~/Library/LaunchAgents/com.karlmarx.finflow-sync.plist
launchctl list | grep finflow-sync       # verify registered
launchctl start com.karlmarx.finflow-sync # optional: trigger now
tail -f ~/.local/share/finflow-sync/stdout.log
```

Exit codes from `teller_pull`:

| Code | Meaning |
|------|---------|
| 0 | Sync completed (zero or more enrollments, no fatal failures) |
| 1 | Crash before iterating (config missing, DB unwritable, etc.) |
| 2 | Every enrollment errored — likely auth/network problem worth investigating |

The plist intentionally embeds **no secret material**. `TELLER_APP_ID` and `TELLER_ENV` come from `~/finflow/.env` via pydantic-settings (working directory set to `/Users/kmx/finflow`). The mTLS cert + key are read from `certs/certificate.pem` and `certs/private_key.pem`. Per-enrollment `access_token` lives in DuckDB, never in env. Contrast with `com.karlmarx.nextcloud-sync.plist`, which currently inlines `NEXTCLOUD_PASSWORD` in plaintext — that pattern was not replicated here.

### Required state on disk

| Path | Purpose | Source |
|------|---------|--------|
| `certs/certificate.pem` | Teller mTLS client cert | Download from Teller dashboard |
| `certs/private_key.pem` | Teller mTLS private key | Download from Teller dashboard |
| `.env` (`TELLER_APP_ID`, `TELLER_ENV`, etc.) | Pydantic Settings env file | Copy `.env.example`, fill in Teller app ID |
| `finflow.duckdb` (default) | Local transaction store | Created on first startup by `db/schema.py:initialize_db()` |

`certs/` is git-ignored. `TELLER_ENV` defaults to `sandbox` — flip to `development` or `production` per Teller's tier.

## Data flow

```
Frontend (index.html + connect.js)
  │ user clicks "Connect"
  ▼
POST /api/teller/enroll          → backend issues Teller Connect config
  │
Teller Connect widget (browser)  → user logs into bank, returns enrollment.access_token
  │
POST /api/teller/save            → store enrollment in DuckDB.enrollments
POST /api/teller/sync            → for each enrollment: httpx (mTLS) → Teller API
                                   → upsert transactions → DuckDB.transactions
GET  /api/accounts               → list connected accounts
GET  /api/transactions           → filter by start_date / end_date / limit
GET  /api/transactions/summary   → Polars groupby category aggregation
```

DuckDB schema (two tables): `enrollments` (one per linked institution, holds access_token) and `transactions` (upsert-keyed for idempotent re-syncs).

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/teller/enroll` | Get Teller Connect config |
| POST | `/api/teller/save` | Save enrollment access_token |
| POST | `/api/teller/sync` | Sync transactions for all enrollments |
| GET | `/api/accounts` | List accounts |
| GET | `/api/transactions` | List transactions (`?start_date=&end_date=&limit=`) |
| GET | `/api/transactions/summary` | Spending by category (Polars) |

## Status

**Working alpha, hourly sync staged but not yet activated.** Last meaningful change: `2026-04-04` — migrated off Plaid to Teller (`def1a2f`). 2026-05-09: added `finflow.tasks.teller_pull` one-shot and staged the hourly LaunchAgent (Karl to `launchctl load` after inspection). No tests yet, no CI.

## Open questions / known issues

- **Teller free-tier rate limit gate is still open.** Teller doesn't publish exact RPS/RPH thresholds for free-tier. WebSearch 2026-05-09 confirmed the limits are intentionally private. Hourly sync against a single enrollment with a few accounts is well below any plausible threshold (~5–10 calls/hour: 1 `/accounts` + N `/accounts/<id>/transactions`), but the gate stays open formally until 24h of production runs come back without 429s. Watch `stderr.log` for `httpx.HTTPStatusError: 429` after activation.
- **Pre-activation gate: no `.env` and `certs/` is empty `.gitkeep` only.** finflow has never been used against real Teller credentials on this machine. The plist will fire and exit 0 (no enrollments) until at least one bank is enrolled via the web UI.
- `TELLER_ENV=sandbox` is the default; production data requires flipping the env var and uploading production certs.
- No backup story for `finflow.duckdb` yet — it's only as durable as the disk it lives on. Once the hourly sync is live this becomes more important.
- Teller cert + key are plaintext on disk under `certs/` (git-ignored). Treat the directory like KeePass-adjacent material.
- `dev` extras (`pytest`, `ruff`) declared but no `tests/` directory exists.
- No alerting on sync failure yet. Exit code 2 (all enrollments failed) is logged to stderr but not surfaced anywhere — wire to Discord/Healthchecks.io later.

## Cross-references

- [auto-dashboard.md](auto-dashboard.md) — should get a `finflow` node once it's running on a schedule
- [command-center.md](command-center.md) — natural consumer of `/api/transactions/summary` for a spending widget
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
