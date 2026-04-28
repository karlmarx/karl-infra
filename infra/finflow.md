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

Manual local server — no LaunchAgent, no remote deployment. Dev loop:

```bash
cd ~/finflow
uv sync
uv run uvicorn finflow.main:app --reload   # or `uv run finflow` (project script)
```

Open http://localhost:8000 — the static `frontend/index.html` hosts the Teller Connect widget. Auto-generated OpenAPI docs at `/docs`.

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

**Working alpha, manual-run only.** Last meaningful change: `2026-04-04` — migrated off Plaid to Teller (`def1a2f`). Three commits total. No tests yet, no CI, no scheduled syncs — `/api/teller/sync` is hand-fired today.

## Open questions / known issues

- No automation: there's no LaunchAgent, no cron, no `command-center` integration. Sync only runs when the user POSTs.
- `TELLER_ENV=sandbox` is the default; production data requires flipping the env var and uploading production certs.
- No backup story for `finflow.duckdb` yet — it's only as durable as the disk it lives on.
- Teller cert + key are plaintext on disk under `certs/` (git-ignored). Treat the directory like KeePass-adjacent material.
- `dev` extras (`pytest`, `ruff`) declared but no `tests/` directory exists.

## Cross-references

- [auto-dashboard.md](auto-dashboard.md) — should get a `finflow` node once it's running on a schedule
- [command-center.md](command-center.md) — natural consumer of `/api/transactions/summary` for a spending widget
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
