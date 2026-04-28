# Find Hub Tracker

> **PLANNED — not yet deployed.** Status is "built, deploy pending"; no production instance running on the seedbox or anywhere else as of 2026-04-26.

Google Find Hub device tracker with Discord alerts and healthchecks monitoring. Intended target: ultra.cc seedbox as a systemd user service.

## Overview

| Field | Value |
|-------|-------|
| Repo | [karlmarx/find-hub-tracker](https://github.com/karlmarx/find-hub-tracker) |
| Status | Built, deploy to ultra.cc pending |
| Deployment target | ultra.cc seedbox (systemd user service) |
| Stack | Python 3.14+, APScheduler, GoogleFindMyTools (reverse-engineered Nova API) |
| Database | PostgreSQL (primary), SQLite (fallback) |
| Monitoring | healthchecks.io (dead man's switch ping) |

## Purpose

Polls the Google Find Hub API (reverse-engineered Nova API via GoogleFindMyTools) at regular intervals to track device location and battery level. Sends Discord alerts when:

- Device leaves a geofenced area
- Battery drops below threshold (wearables: Pixel Watch, Pixel Buds)
- 6-hour periodic summaries
- 24-hour data pruning

## Architecture (planned)

```
systemd user service (ultra.cc)
  → find-hub-tracker (Python + APScheduler)
     → Google Find Hub Nova API (5-min location poll, 15-min battery check)
     → PostgreSQL / SQLite (location + battery history)
     → Discord webhook (alerts + periodic summaries)
     → Healthchecks.io (dead man's switch ping)
```

## Deployment plan

- `deploy_ultra.sh` script in the repo for ultra.cc setup
- systemd user service for persistent background operation
- Configurable alert thresholds via environment variables
- Slot is reserved alongside existing seedbox services (Nextcloud, etc.) — see [../ARCHITECTURE.md](../ARCHITECTURE.md) seedbox section.

## Open issues

| # | Title |
|---|-------|
| [#4](https://github.com/karlmarx/find-hub-tracker/issues/4) | Dead man's switch — alert when tracker stops |
| [#3](https://github.com/karlmarx/find-hub-tracker/issues/3) | Migrate periodic tasks from Windows WSL to dedicated infra |
| [#2](https://github.com/karlmarx/find-hub-tracker/issues/2) | Design shared schema for multi-service automation |
| [#1](https://github.com/karlmarx/find-hub-tracker/issues/1) | Evaluate 2018 MacBook as home automation server |

## Cross-references

- [local-windows.md](local-windows.md) — currently lists this in the migration-plans section.
- [../ARCHITECTURE.md](../ARCHITECTURE.md) — seedbox section is the deploy target.
- Note: the previous version of this doc lived at `~/karl-infra/services/find-hub-tracker.md`. This file replaces it as the canonical infra doc; the services file can be removed.
