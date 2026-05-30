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

## Features (v2, 2026-05-30)

- **Web map redesign**: CartoDB dark tiles, pulsing live dot, glassy status card,
  recenter + 12h-trail toggle.
- **12h history trail**: `/api/history`; downsampled (8m / 60s gate), active-only,
  pruned to 12h, capped 2000 pts. Map splits the polyline across >3min gaps.
- **Place/activity engine**: KV key `places` = `[{name,type,lat,lng,radius_m,url?}]`.
  `/api/location` returns matched `place` + `activity` (speed-derived: still/walking/
  running/cycling/driving). Map renders emoji markers (home/gym/yoga/pickleball/…)
  and a "📹 Watch live" chip when the matched place has a `url`.
  - Authenticated `POST /places` (Bearer INGEST_TOKEN) replaces the list;
    `GET /api/places` returns names+types only (no coords).
  - Seeded places (2026-05-30): Home, Amped (gym), LA Fitness (gym), Holiday Park
    Pickleball (url → parkviewlive.com live cam). Derived by clustering geotagged
    photo EXIF — see `tools/cluster_places.py` in the repo.
- **App**: token auto-saves (doAfterTextChanged), map URL is a tappable link,
  background-location ("Allow all the time") requested after fine grant.

## Cloudflare Access exception

The account has a single Access app **`93.fyi Subdomains`** gating `*.93.fyi`
(zero-trust login). To keep `where.93.fyi` public, a more-specific self-hosted
Access app **`where.93.fyi (public map)`** (id `73938a7d-…`) was created with a
single **Bypass / Everyone** policy. Exact-hostname apps win over the wildcard,
so the map is public while every other subdomain stays gated. To re-gate, delete
that app.

## Status (2026-05-30) — LIVE

- [x] Deployed via Cloudflare **Global API Key** (KeePass `cloudflare.com` →
      `Global API Key` field; account email `karlmarx9193@gmail.com`). KV id
      `bd3c1896b499461f9a3e85a854105b39` wired into `wrangler.toml`. `INGEST_TOKEN`
      secret set on the Worker. `where.93.fyi` custom domain provisioned.
- [x] Access bypass created so the map is publicly reachable (see above).
- [x] APK builds: toolchain installed (openjdk@17, android-commandlinetools,
      SDK at `~/Library/Android/sdk`, platform-34 + build-tools 34.0.0). Debug APK
      at `android/app/build/outputs/apk/debug/app-debug.apk` (6 MB).
- [ ] Install the APK on the Pixel, paste the `INGEST_TOKEN` into the app, toggle on.
- [ ] (Optional) CI: the deploy GitHub Action expects a **scoped**
      `CLOUDFLARE_API_TOKEN` repo secret (Workers Scripts + KV + Zone/DNS). Don't
      put the global key in GitHub — mint a scoped token if CI deploys are wanted.

> Build gotcha fixed: the hand-written `gradlew` shipped `DEFAULT_JVM_OPTS` with
> literal embedded quotes, so `java` got `"-Xmx64m"` as a classname. Fixed to
> unquoted `-Xmx64m -Xms64m`.

## Origin

Rebuilt locally from scratch after a claude.ai/code **cloud** session
(`session_018bkwavpKS1MZQq4LeBxyo6`, branch
`claude/location-sharing-android-app-UH8SO`) stalled — its sandbox died before
pushing, so none of the work survived. Lesson: cloud sandboxes are ephemeral;
the durable artifact is the pushed git repo.
