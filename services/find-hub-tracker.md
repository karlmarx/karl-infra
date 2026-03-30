# Find Hub Tracker

> Google Find Hub device tracker with Discord integration

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/find-hub-tracker](https://github.com/karlmarx/find-hub-tracker) |
| **Status** | Scaffolded, not yet deployed |
| **Planned Deployment** | ultra.cc seedbox |
| **Stack** | Python |

## Purpose

Polls the Google Find Hub API at regular intervals to track device location and battery level. Sends Discord alerts when:
- Device leaves a geofenced area
- Battery drops below threshold
- Tracker stops reporting (dead man's switch)

## Planned Architecture

```
Cron / systemd timer (ultra.cc)
  -> find-hub-tracker (Python)
     -> Google Find Hub API (poll location/battery)
     -> Discord webhook (alerts)
     -> Healthchecks.io (dead man's switch ping)
```

## Open Issues

| # | Title |
|---|-------|
| [#4](https://github.com/karlmarx/find-hub-tracker/issues/4) | Dead man's switch — alert when tracker stops |
| [#3](https://github.com/karlmarx/find-hub-tracker/issues/3) | Migrate periodic tasks from Windows WSL to dedicated infra |
| [#2](https://github.com/karlmarx/find-hub-tracker/issues/2) | Design shared schema for multi-service automation |
| [#1](https://github.com/karlmarx/find-hub-tracker/issues/1) | Evaluate 2018 MacBook as home automation server |
