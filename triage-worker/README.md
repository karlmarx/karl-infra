# triage-worker

Event-driven email triage on a Cloudflare Worker, doubling as an MCP gateway
for Karl's connected services.

## What it does

- **Cron, every 1 min**: polls Gmail for new messages from the sender allowlist.
- For each match, runs an Anthropic agent loop (Haiku 4.5 + prompt caching)
  that calls tools to:
  - apply a Gmail label (`triaged/urgent` | `normal` | `low` | `bug` | `spam`),
  - create a Todoist task (if action needed),
  - create a GitHub issue (if it's a bug/code report),
  - create a Gmail draft reply (never sent).
- Streams every step to a Durable Object activity log, consumed by the
  `/triage` page in `karl-command-center`.
- Exposes the same tools over an MCP-shaped JSON-RPC endpoint at `/mcp` so
  any MCP client (Claude Desktop, LibreChat, custom) can use them.

## Guardrails (billing protection)

| Guard | Default | Where |
|---|---|---|
| Sender allowlist | `karlmarx9193@gmail.com,k@93.fyi` | `SENDER_ALLOWLIST` var |
| Daily $ cap | `$1.00` | `DAILY_BUDGET_USD` var |
| Daily triage count cap | `50` | `MAX_TRIAGES_PER_DAY` var |
| Per-triage token cap | `8000` | `MAX_TOKENS_PER_TRIAGE` var |
| Per-triage iteration cap | `6` | `MAX_ITERATIONS` in `triage.ts` |
| Auth on `/trigger`, `/chat`, `/mcp` | `MCP_SHARED_SECRET` | secret |

When any cap is hit, the worker logs a `budget.exceeded` event and stops.
State resets at UTC midnight.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/` | none | health |
| GET | `/budget` | none | current daily spend + count |
| GET | `/activity?limit=100` | none | recent events |
| GET | `/activity/stream` | none | SSE of new events |
| POST | `/trigger` | Bearer | manually run a poll |
| POST | `/chat` | Bearer | JSON `{messages: []}`, runs agent loop with tools |
| POST | `/mcp` | Bearer | MCP JSON-RPC (`initialize`, `tools/list`, `tools/call`) |

## Setup

### 1. Install + log in

```bash
cd karl-infra/triage-worker
npm install
npx wrangler login
```

### 2. Get a Google OAuth refresh token

You need a Google OAuth 2.0 client (Desktop type) with the
`https://www.googleapis.com/auth/gmail.modify` scope authorized.

Easiest path: use the [OAuth Playground](https://developers.google.com/oauthplayground/):

1. Click the gear icon, check "Use your own OAuth credentials", paste your
   client ID and secret.
2. In the left panel, paste `https://www.googleapis.com/auth/gmail.modify`
   and click "Authorize APIs".
3. Sign in as the account that receives the emails (`karlmarx9193@gmail.com`).
4. Click "Exchange authorization code for tokens".
5. Copy the **refresh token**. It does not expire unless you revoke it.

Alternatively, run `node scripts/get-gmail-refresh-token.mjs` (see that file).

### 3. Set secrets

```bash
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put GOOGLE_REFRESH_TOKEN
npx wrangler secret put TODOIST_TOKEN
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put MCP_SHARED_SECRET   # generate any random string
```

### 4. Adjust vars in `wrangler.toml`

Confirm `SENDER_ALLOWLIST` contains your two email addresses. Update
`DEFAULT_GH_REPO` if you want issues created somewhere other than
`karlmarx/karl-command-center`.

### 5. Local dev

```bash
cp .dev.vars.example .dev.vars
# fill in real values
npm run dev
```

Then in another terminal:

```bash
curl http://localhost:8787/budget
curl -X POST -H "authorization: Bearer <MCP_SHARED_SECRET>" http://localhost:8787/trigger
```

### 6. Deploy

```bash
npm run deploy
npx wrangler tail
```

The worker will be at `https://triage-worker.<your-subdomain>.workers.dev`.
Set that URL + the shared secret in `karl-command-center`:

```
TRIAGE_WORKER_URL=https://triage-worker.<your-subdomain>.workers.dev
TRIAGE_WORKER_SECRET=<MCP_SHARED_SECRET>
```

## Cost estimate

Per triaged email (Haiku 4.5 with prompt caching after first call):

| Component | Tokens | $ |
|---|---|---|
| Cached system + tools | 1500 (read) | $0.00015 |
| Fresh input (email body) | ~600 | $0.0006 |
| Output (tool calls + summary) | ~400 | $0.002 |
| **Per triage** | | **~$0.003** |

At 10 emails/day → **~$1/month**. The hard cap is $1/day, so the worst case
is **~$30/month** if something goes wrong (and the worker would stop you long
before that).

## Files

```
src/
├── index.ts         # Worker entry (HTTP + scheduled)
├── env.ts           # Env binding types
├── types.ts         # Shared shapes
├── state.ts         # TriageStateDO (budget, activity log, OAuth cache, dedupe)
├── guardrails.ts    # Preflight, charge, allowlist
├── tools.ts         # Anthropic tool schemas + dispatch
├── triage.ts        # Per-email agent loop
├── chat.ts          # General-purpose chat agent loop
├── poll.ts          # Cron handler
├── mcp.ts           # JSON-RPC MCP endpoint
└── adapters/
    ├── gmail.ts
    ├── todoist.ts
    └── github.ts
```
