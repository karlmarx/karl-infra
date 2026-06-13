# relayhub-scout

**Purpose:** A self-contained demo of an AI support-investigation agent ("RelayHub
Scout") for a fictional multi-tenant integration platform. Built as a blueprint /
reference for token-disciplined agent architecture (tiered tool funnel, sub-agent
token firewall, browser handoff, human-gated knowledge base). Not production infra.

**Repo:** `github.com/karlmarx/relayhub-scout-demo` (PRIVATE). Blueprint guidance for
agents lives in the repo's `CLAUDE.md`.

## Components

- **Frontend** (`web/`): Vite + React 18 + TS + Tailwind 3. Mission-control dark
  dashboard. Deployed to Vercel → **scout.93.fyi**.
- **Backend** (`services/`): four FastAPI services + MongoDB 7 (Docker Compose).
  - `providers` — mock external providers + chaos middleware
  - `gateway` — proxies tenant requests, writes transaction + audit trail
  - `integrations` — mock CRM/Jira/GitLab
  - `agent` — orchestrator loop (Sonnet 4.6), 16 tiered tools, sub-agent firewall
    (Haiku 4.5), Google OIDC auth. The only service that calls Anthropic.

## Deploy path

```
push to karlmarx/relayhub-scout-demo (main, web/ rootDir)
        │  Vercel GitHub auto-deploy (rootDirectory=web)
        ▼
   Vercel project karlmarxs-projects/relayhub-scout
        │  CNAME scout.93.fyi → cname.vercel-dns.com (proxied:false)
        ▼
   https://scout.93.fyi   (deployment protection OFF — public)
```

## ⚠️ Hosted frontend is a PREVIEW, not a live demo

The frontend calls the agent backend at `VITE_AGENT_URL` (default `/api`). That
backend is a **local Docker/Python/Mongo stack** and is **not deployed** (it can't run
on Vercel/Workers as-is). So `scout.93.fyi` loads but shows its "configure / connect"
state until:

1. `VITE_AGENT_URL` (Vercel env) points at a reachable agent backend (e.g. a
   `cloudflared` tunnel to the local stack, or a VM/host running `make up`), and
2. that origin (`https://scout.93.fyi`) is added to the Google OAuth client's
   *Authorized JavaScript origins*, and `GOOGLE_CLIENT_ID` is set.

To run the full demo: clone the repo, `cp .env.example .env` (add the three secrets),
`make up && make seed`, open `localhost:5173`.

## Cross-refs

- Domain: `diagrams/domains.md` → scout.93.fyi
- Vercel table: `ARCHITECTURE.md` → relayhub-scout
- Standing rule: concierge-bot (separate CF Worker repo) reuses this repo's adapter
  Protocol pattern, not its runtime.
