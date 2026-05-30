# where.93.fyi — Location Broadcast

Broadcast Karl's phone location to a **fully public** live map at
`https://where.93.fyi`, controlled by an on/off toggle in a native Android app.

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/where-93fyi](https://github.com/karlmarx/where-93fyi) (private) |
| **Public URL** | https://where.93.fyi |
| **Backend** | Cloudflare Worker `where-93fyi` (account `f1ccbe18…`) |
| **Storage** | Cloudflare KV namespace `where-93fyi-location`, single key `current` |
| **Android** | Native Kotlin app, package `fyi.karl.where93` |
| **Created** | 2026-05-30 |

> ⚠️ The map is **public to anyone with the URL** while broadcasting is on. The
> only privacy control is the app toggle. This was an explicit decision.

## Components

1. **Cloudflare Worker** (`worker/src/index.js`) — one Worker, three routes:
   - `POST /ingest` — authenticated (`Authorization: Bearer <INGEST_TOKEN>`),
     writes the latest fix to KV. `{active:false}` clears the live state.
   - `GET /api/location` — public JSON read, returns latest fix + derived
     `stale` flag (fix older than 90s while active → stale).
   - `GET /` — public Leaflet/OSM map page that polls `/api/location` every 5s.
2. **Android app** (`android/`) — native Kotlin, View-based UI:
   - Single broadcast on/off toggle + in-app status dot.
   - Foreground location service (`FusedLocationProvider`, 15s interval,
     `foregroundServiceType="location"`) → POSTs to `/ingest`.
   - Persistent status-bar notification while live (platform requirement +
     "broadcast is live" indicator) with a Stop action.
   - Quick Settings tile (`BroadcastTileService`) to toggle from the shade.
3. **Deploy automation** — `setup.sh` (one-shot KV create + secret + deploy) and
   `.github/workflows/deploy-worker.yml` (CI deploy on push to `worker/`).

## Data flow

```
Android FGS ──POST /ingest (Bearer)──▶ Worker ──put──▶ KV "current"
                                          ▲                 │
browser ──GET / (map) ──poll /api/location ┘◀──get──────────┘
```

No location history is stored — last-write-wins on one KV key, by design.

## Secrets / tokens

- **`INGEST_TOKEN`** — shared secret. Set on the Worker via
  `wrangler secret put INGEST_TOKEN`; the same value is pasted into the Android
  app's settings (stored in app-private SharedPreferences). Generate with
  `openssl rand -hex 24`.
- **`CLOUDFLARE_API_TOKEN`** — deploy token. Needs `Workers Scripts:Edit`,
  `Workers KV Storage:Edit`, `Zone:Edit` + `DNS:Edit` on 93.fyi. Used by
  `setup.sh` locally and as a GitHub Actions secret for CI.

## Status / open items (2026-05-30)

- [ ] Run `setup.sh` with a scoped `CLOUDFLARE_API_TOKEN` (KV id is currently a
      placeholder in `wrangler.toml`; not yet deployed).
- [ ] Build the APK (needs Android Studio / JDK 17 + Android SDK — not yet
      installed on the Mac Studio).
- [ ] Add `CLOUDFLARE_API_TOKEN` GitHub Actions secret for CI deploys.

## Origin

Rebuilt locally from scratch after a claude.ai/code **cloud** session
(`session_018bkwavpKS1MZQq4LeBxyo6`, branch
`claude/location-sharing-android-app-UH8SO`) stalled — its sandbox died before
pushing, so none of the work survived. Lesson: cloud sandboxes are ephemeral;
the durable artifact is the pushed git repo.
