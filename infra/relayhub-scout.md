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
- **Backend** (`services/`): four FastAPI services + MongoDB 7. Runs locally via
  Docker Compose, and hosted as one self-contained container on a free **Hugging
  Face Space** (`karlmarxxx/relayhub-scout-api`, Docker SDK, mongod + all services +
  deterministic re-seed on boot; ephemeral storage → always-fresh).
  - `providers` — mock external providers + chaos middleware
  - `gateway` — proxies tenant requests, writes transaction + audit trail
  - `integrations` — mock CRM/Jira/GitLab
  - `agent` — orchestrator loop (Sonnet 4.6), 16 tiered tools, sub-agent firewall
    (Haiku 4.5), Google OIDC auth. The only service that calls Anthropic.

## Deploy path (LIVE)

```
GitHub karlmarx/relayhub-scout-demo (main)
   ├─ web/  ──Vercel auto-deploy (rootDir=web)──► scout.93.fyi (CNAME, protection off)
   │                                                   │ VITE_AGENT_URL
   └─ Dockerfile ──hf upload──► HF Space ◄────────────┘
        karlmarxxx/relayhub-scout-api  →  https://karlmarxxx-relayhub-scout-api.hf.space
        (free CPU; secrets: ANTHROPIC_API_KEY, SERVICE_TOKEN, GOOGLE_CLIENT_ID)
```

`scout.93.fyi` (frontend) → HF Space (backend) is wired and verified: bundle baked
with `VITE_AGENT_URL`, CORS allows the scout origin, `/health` + `/scenarios` + auth
green. CORS is `*`; mutating ops/knowledge endpoints are auth-gated; the HF Space
free tier sleeps after ~48h idle and re-seeds on wake (~30s cold start).

**Remaining for human login:** set `GOOGLE_CLIENT_ID` (Space secret) once the Google
OAuth Web client exists with origin `https://scout.93.fyi`. Read at runtime, so a
Space restart picks it up — no rebuild. (Google's new console rejects `localhost`
origins with a "public TLD" error; a `localdev.93.fyi → 127.0.0.1` record would let
`http://localdev.93.fyi:5173` work for local sign-in.)

Local full demo: clone, `cp .env.example .env` (ANTHROPIC_API_KEY + GOOGLE_CLIENT_ID +
SERVICE_TOKEN), `make up && make seed`, open `localhost:5173`.

## Cross-refs

- Domain: `diagrams/domains.md` → scout.93.fyi
- Vercel table: `ARCHITECTURE.md` → relayhub-scout
- Standing rule: concierge-bot (separate CF Worker repo) reuses this repo's adapter
  Protocol pattern, not its runtime.
