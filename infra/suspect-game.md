# suspect-game — multiplayer word bluffing game

**Domain:** [suspect.93.fyi](https://suspect.93.fyi)
**Repo:** `karlmarx/suspect-game`
**Vercel project:** `suspect-game`
**Realtime backend:** `suspect-game.karlmarx.partykit.dev` (PartyKit cloud, Cloudflare-operated)
**Status:** Live (shipped 2026-05-19, built for Zoom happy hours)

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
| Game state machine | `party/server.ts` | PartyKit Durable Object. One DO per room. Holds Round state, runs phase transitions via `storage.setAlarm()`, validates clues server-side, computes scoring. Filters state per-recipient (Suspect never receives target word). |
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
# Backend (one-time login, then per-deploy)
cd ~/suspect-game
npx partykit deploy   # → suspect-game.karlmarx.partykit.dev

# Frontend (auto-deploys from GitHub `main` after first setup)
git push origin main
```

`VITE_PARTYKIT_HOST=suspect-game.karlmarx.partykit.dev` is set in the Vercel
project env so the SPA dials the deployed PartyKit room.

## Known follow-ups

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
