# suspect-game — multiplayer word bluffing game

**Domain:** [suspect.93.fyi](https://suspect.93.fyi)
**Repo:** `karlmarx/suspect-game`
**Vercel project:** `suspect-game`
**Realtime backend:** `suspect-game.karlmarx.partykit.dev` (legacy PartyKit cloud — Cloudflare-operated; see PartyKit-deprecation note below)
**Status:** Live (shipped 2026-05-19; how-to-play overview + GitHub link added to landing 2026-05-22; built for Zoom happy hours)
**Auth:** None — `VITE_APP_PASSWORD` intentionally unset on Vercel and `APP_PASSWORD` unset on PartyKit. Knowingly shipped open per Karl's "ditch the auth for now" call when wrangler deploy blocked the password rollout. A random password is parked in macOS Keychain at service `suspect-game-app-password` for if/when the gate is re-enabled.

## Purpose

A real-time multiplayer word-deduction game for 3–8 players, designed to
share over Zoom: every player opens `suspect.93.fyi/room/<code>` on their
own device and the app drives the round from one source of truth.

**Mechanic:** everyone sees the same 4×4 word grid. One word is the target.
All players except one (the Suspect) see which word it is. Players take
turns giving one-word clues. The Suspect bluffs. After clues, players vote
on who they think the Suspect is. Scoring rewards both convincing innocents
and bluffing suspects.

Think Codenames meets The Chameleon.

## Components

| Piece | Path | Notes |
|-------|------|-------|
| Game state machine | `worker/server.ts` | partyserver `Server<Env>` (Cloudflare Durable Object) — `GameServer` class. One DO per room. Holds Round state, runs phase transitions via `ctx.storage.setAlarm()`, validates clues server-side, computes scoring. Filters state per-recipient (Suspect never receives target word). |
| Worker entry | `worker/index.ts` | Routes `/parties/main/:room` requests to the DO via partyserver's `routePartykitRequest`. Binding name `Main` (case-insensitive match for the partysocket client's default party name). |
| Worker config | `wrangler.jsonc` | DO binding (`Main` → `GameServer`), `new_sqlite_classes` migration v1, `nodejs_compat`, observability on. Compat date 2025-09-29. |
| Shared types | `src/shared/types.ts` | `ClientMessage` / `ServerMessage` discriminated unions imported by both client and server. Single source of truth for the wire protocol. |
| Word bank | `src/shared/words.ts` | 6 categories × 50+ words: Food & Drink, Animals, Places, Office Life, 80s/90s, Movies. `generateGrid(category)` picks 16 + a target. |
| Realtime hook | `src/hooks/useGameRoom.ts` | Wraps `partysocket` (auto-reconnect, exponential backoff). Persists session ID to localStorage so reload = rejoin same player. |
| Countdown hook | `src/hooks/useCountdown.ts` | Renders `phaseEndsAt - (Date.now() + serverOffset)` so all clients show the same timer regardless of clock skew. |
| Room shell | `src/screens/Room.tsx` | Owns the socket lifecycle. Branches between Lobby / RoundView based on server state. |
| Round view | `src/screens/RoundView.tsx` | Sub-views for each phase: reveal, clue, discuss, vote, suspect-guess, resolution, finished. |
| UI primitives | `src/components/` | WordGrid, Badge, Timer, PageShell, PlayerCard, PrimaryButton, Glow. Tailwind v4 + inline-styled for the neon palette. |
| SPA rewrite | `vercel.json` | All paths fall back to `/index.html` so `/room/ABCD` works on cold load. |

## Data flow

```
Browser (Vite + React, suspect.93.fyi)
    │
    │  WebSocket (PartySocket)
    │     wss://suspect-game.karlmarx.partykit.dev/parties/main/<room-code>
    ▼
PartyKit / Cloudflare Workers
    │
    └── Durable Object instance per room code
        │
        ├── In-memory RoomState (players, round, phase, votes, scores)
        ├── DurableObjectStorage (state persists across hibernation)
        ├── Alarm (drives phase transitions when timers expire)
        └── Per-connection broadcast with per-recipient filtering
             ├── Suspect      → targetWord: null,  suspectId: null
             ├── Innocent     → targetWord: <word>, suspectId: null
             └── Unauth obs.  → targetWord: null,  suspectId: null
```

## Anti-cheat

The Suspect never receives the target word over the wire. This is enforced
in `buildPublicState()` on the server: only sessions that are both
identified-as-a-player AND not the Suspect for the current round get the
target word in their state payload. Anyone else (Suspect, unidentified
observers, future spectator mode) sees `null` for both `targetWord` and
`suspectId` until the resolution phase.

Validated end-to-end with isolated browser contexts during local dev: a raw
WebSocket connection opened with no `join` message receives `null` for both
fields.

## Scoring

| Outcome | Points |
|---|---|
| Voted correctly to catch the Suspect | +2 |
| Suspect caught but guesses target word | +2 (Suspect), 0 (everyone else) |
| Suspect escapes (wrong-majority vote or tie) | +3 (Suspect) |
| Innocent received zero votes (good blending) | +1 bonus |

Game length defaults to `players.length × 2` rounds (so everyone is Suspect
roughly twice). Configurable in the lobby (3–20).

## Deploy

```bash
# Frontend (auto-deploys from GitHub `main`)
git push origin main

# Backend — PARTLY STUCK (see PartyKit deprecation below). Current state:
#   running runtime = legacy suspect-game.karlmarx.partykit.dev (no password check)
#   in-repo code    = partyserver, ready to ship to Workers but not yet deployed
```

`VITE_PARTYKIT_HOST=suspect-game.karlmarx.partykit.dev` is set in the Vercel
project env (Production scope) so the SPA dials the legacy PartyKit room.

### PartyKit deprecation status (as of 2026-05-22)

The hosted PartyKit platform stopped issuing new-deploy entitlements on
Karl's account — `partykit deploy` returns `entitlements.not_available`.
The existing deployment at `suspect-game.karlmarx.partykit.dev` keeps
serving (Cloudflare Worker behind the scenes), but the code there is the
original pre-password-gate version and cannot be updated.

A migration to [partyserver](https://github.com/cloudflare/partykit) on
Workers + Durable Objects is **already in the repo** (`worker/`,
`wrangler.jsonc`) but not yet deployed because that requires an interactive
`wrangler login` Karl wasn't able to complete in the deploy session.

To finish the migration later:

```bash
cd ~/suspect-game
npx wrangler login                                  # interactive OAuth
npm run deploy:worker                               # → suspect-game-server.<account>.workers.dev
# Optional password gate:
PW=$(security find-generic-password -a "$USER" -s "suspect-game-app-password" -w)
echo "$PW" | npx wrangler secret put APP_PASSWORD
vercel env rm VITE_PARTYKIT_HOST production -y
echo "suspect-game-server.<account>.workers.dev" | vercel env add VITE_PARTYKIT_HOST production
# (Optional) echo "$PW" | vercel env add VITE_APP_PASSWORD production
vercel --prod
```

After that, traffic moves from `*.partykit.dev` to `*.workers.dev` and the
old PartyKit deployment is orphaned. See [[partykit-deprecated]] in memory.

## Known follow-ups

- **Wrangler deploy of the new partyserver worker** (see PartyKit deprecation
  section above). Until done, the password-gate code lives in the repo but
  isn't actually enforced anywhere.
- **Suspect rotation:** currently pure random; spec says "everyone should be
  Suspect roughly equally." Add weighted selection that prefers players who
  have been Suspect the fewest times.
- **Clue input UX:** the input clears when the server rejects the clue
  (e.g. for matching a grid word). Should preserve text + show the error
  inline rather than as a toast.
- **In-app chat for discussion phase:** spec stretch goal. Today, the
  discussion phase relies on Zoom audio.
- **Screen-share-safe mode:** show the grid only, hide role assignment.
  Spec stretch goal.

## Cross-refs

- [[domain-93fyi]] — DNS zone config
- [[domains]] (diagrams) — CNAME assignments table
- [[partykit-deprecated]] (memory) — note that PartyKit hosted no longer accepts new deploys; reach for Workers + DO directly on the next multiplayer project.
