---
name: site-health
description: Check that every 93.fyi site is up, still public or private as expected, and has a valid TLS cert. Use for scheduled health checks or when Karl asks "are my sites up?".
---

# site-health

## Run

```bash
python3 ~/.hermes/skills/site-health/check_sites.py
```

- Exit 0 + no output: everything is fine. On a **scheduled** run, reply with exactly
  `[SILENT]` (or nothing) so Karl is not messaged. On a run Karl asked for, say
  "All N sites OK" (use `--verbose` to get the list).
- Exit 1: each output line is one problem. Send Karl a short Telegram message:
  one bullet per problem, worst first (DOWN, EXPOSED, LOCKED, TLS, CHANGED), then a
  one-line suggested fix for each.

## Before alerting on DOWN

Re-run the script once after ~60 seconds. Only alert if the same host fails twice,
so a single blip doesn't page Karl.

## Problem types

| Tag | Meaning | Usual fix |
|-----|---------|-----------|
| DOWN | error, timeout, or 4xx/5xx | Check the Vercel project's latest deployment (or the Cloudflare Worker for `where`/`balls`) |
| EXPOSED | private site returned 200 | Cloudflare DNS record got unproxied, or its Access app was removed |
| LOCKED | public site redirects to Access login | DNS record got proxied. Public Vercel sites must be DNS only |
| TLS | cert expires in <14 days | Vercel → project → Domains → refresh the domain |
| CHANGED | status differs from baseline | Look manually. If intended, update `sites.json` |

## Adding a site

Add `"<name>.93.fyi": "public" | "access" | "login"` to `sites.json`.
