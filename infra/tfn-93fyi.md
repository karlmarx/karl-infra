# tfn-93fyi — Twilio DTMF Backdoor + Visitor Helpline

**Status:** **LIVE** (2026-05-31). Number wired → `tfn.93.fyi`; routes verified in prod (signed request → 200 valid single-`<Response>` TwiML, unsigned → 403). Standalone repo + Vercel project shipped. Not yet *distributed* (Karl isn't handing the number out until the go.93.fyi directions reshoot is confirmed). Mac executor committed but launchd not loaded.

**Purpose:** Turn Karl's unused toll-free number (+1 888 601-6132) into a dual-purpose voice line:
1. **DTMF backdoor** — Karl (whitelisted) calls and triggers actions on his Mac Studio + cloud via touch-tone or a voice agent.
2. **Visitor helpline** — everyone else reaches a multilingual audio companion to go.93.fyi (apartment-finding directions).

---

## Architecture

```
Caller → Twilio (+1 888 601-6132)
           │  voice webhook (POST, X-Twilio-Signature verified)
           ▼
     Vercel: tfn-93fyi  (Next.js App Router, Node runtime) → tfn.93.fyi
      app/api/tfn-backdoor/*
           │
           ├─ whitelist (Karl's cell) ──→ DTMF backdoor menu
           │     1 status / 2 day (safe, inline)
           │     3-8 Mac actions ──→ Upstash Redis queue ──→ Mac executor (BLPOP)
           │     0 ──→ voice agent (ElevenLabs, flagged)
           │
           └─ everyone else ──→ visitor helpline
                 press 1-6 language → directions overview
                 English: full menu (gate/code/voicemail)
                 hidden 9 → PIN gate → safe backdoor subset
```

**Key boundary:** The Mac never exposes a public port. Vercel enqueues intents to Upstash; the Mac polls (BLPOP) and writes results back. Twilio only ever talks to Vercel.

---

## Components

| Layer | Tech | Location |
|-------|------|----------|
| Voice front | Twilio Programmable Voice | +1 888 601-6132 (SID `PN57f41a69da47ad60c107b515aea752ae`) |
| Webhook + logic | Next.js on Vercel | `karlmarx/tfn-93fyi` → `tfn.93.fyi` |
| Queue | Upstash Redis (global) | `tfn:*` keys |
| Executor | Python daemon (launchd) | `~/karl-infra/services/tfn-backdoor/` |
| Notify | Discord webhook | `tfn:audit` + push |

---

## Deployment (live state)

- **Repo:** `karlmarx/tfn-93fyi` (private). Commits: `0c84553` (init), `0cb284c` (plan doc). Pushed to GitHub; Vercel git-connected → push to `main` auto-deploys.
- **Vercel project:** `karlmarxs-projects/tfn-93fyi` (`prj_xgp6LcwTd7M3071qGqUYceHqcqFv`). First prod deploy via CLI 2026-05-31.
- **Domain:** `tfn.93.fyi` — Cloudflare `CNAME tfn → cname.vercel-dns.com`, **proxied:false** (DNS-only). Grey-cloud is required so Twilio reaches Vercel's origin without hitting the CF proxy / Access login wall. TLS issued by Vercel; root returns 200.
- **Twilio:** IncomingPhoneNumber `PN57f41a69da47ad60c107b515aea752ae`, `voice_url = https://tfn.93.fyi/api/tfn-backdoor/voice`, `voice_method = POST` (was the Twilio demo TwiML bin `https://demo.twilio.com/welcome/voice/`).
- **Env:** Production + Development each carry `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `VOICE_PROVIDER=twilio`, `TFN_PIN=9193`, `PUBLIC_BASE_URL=https://tfn.93.fyi` (7 each). **Preview env intentionally skipped** — this project ships push-to-main→production with no PR-preview workflow for the webhook. **`TFN_WHITELIST` is unset** → every caller (incl. Karl's cell) currently lands on the *helpline*; backdoor reachable only via hidden `9` + PIN until the cell # is added. **`NOTIFY_WEBHOOK_URL` unset** → audit notify is a no-op until set.

---

## KV contract (Upstash)

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `tfn:intents:pending` | LIST | — | enqueued actions (Mac BLPOPs) |
| `tfn:result:<id>` | STRING | 300s | action result for poll-back |
| `tfn:status:current` | STRING | 180s | latest Mac status snapshot |
| `tfn:audit` | LIST | capped 1000 | audit log of all calls/actions |
| `tfn:pinfail:<from>` | counter | 3600s | PIN brute-force throttle |

Mac side reads the `rediss://` URL from Keychain `nwb-tfn-redis-url`; Vercel side uses the REST `KV_REST_API_*` pair. Same Upstash global DB.

---

## Digit map

| Digit | Action | Tier | Target |
|-------|--------|------|--------|
| 1 | status | safe | read |
| 2 | day | safe | read |
| 3 | restart_sync | full | mac |
| 4 | restart_photo | full | mac |
| 5 | resume_jobs | full | mac |
| 6 | deploy_nfit | full | cloud |
| 7 | checkin | safe | cloud |
| 8 | wake | full | mac |
| 0 | agent | full | — |

---

## Auth model

- **Whitelist** (Karl's cell, E.164 in `TFN_WHITELIST`) → full access, no PIN.
- **PIN `9193`** (`TFN_PIN`) → unlocks safe read-only subset for non-whitelist callers via hidden digit 9.
- PIN throttle: 3 attempts per call, lockout after 5 fails/hour (`tfn:pinfail:<from>`).
- All Twilio requests verified via `X-Twilio-Signature` (HMAC-SHA1, constant-time compare). Each route signs against `PUBLIC_BASE_URL + path + querystring`, so `PUBLIC_BASE_URL` must exactly equal the public host Twilio calls (`https://tfn.93.fyi`).

---

## TwiML shape (verified, not buggy)

`voice.ts` exposes `gatherMenu(text, provider, base)` = `twiml(gatherMenuInner(...))`, which wraps the `<Gather>` + post-timeout fallback (`<Say>` + `<Hangup/>`) in exactly **one** `<Response>`. The helpline route builds its own single-`<Response>` document the same way. Live signed test confirmed exactly one `<Response>` open/close. (No nested-Response bug — an earlier worklog note to the contrary was mistaken.)

---

## Files

- **Vercel app:** `karlmarx/tfn-93fyi` repo — `app/api/tfn-backdoor/*` (voice, dispatch, result, tts, helpline, voicemail, agent-tool) + `lib/tfn/*` (signature, kv, auth, actions, voice, notify, helpline, helpline-scripts, helpline-translations.json, tts). 27 vitest unit tests. (Migrated out of `nwb-plan` for blast-radius isolation ahead of the arbitrary-shell capability.)
- **Mac executor:** `~/karl-infra/services/tfn-backdoor/` (kv.py, registry.py, handlers.py, status.py, notify.py, agent.py + pytest).
- **launchd:** `~/karl-infra/services/launchd/com.karlmarx.tfn-backdoor.plist`
- **Implementation plan:** preserved in the repo at `docs/plan-2026-05-30.md`
- **Spec:** this file

---

## Open items

- [x] Wire Twilio number webhook → `tfn.93.fyi` (2026-05-31)
- [ ] `TFN_WHITELIST` = Karl's cell (E.164) — until set, Karl's own calls hit the helpline
- [ ] `NOTIFY_WEBHOOK_URL` = Discord webhook — until set, audit notify is a no-op
- [ ] Load launchd executor on Mac (Keychain unlock decision pending) — `status.py` RAM metric bug to fix first (`top` "unused" underreports; reports critical)
- [ ] Verify final directions text after go.93.fyi entrance reshoot, before distributing the number
- [ ] ElevenLabs voice (Phase C/E, optional — cancel at cycle end)
- [ ] Review machine translations (es/de/fr/tr/cs)
- [ ] Next capability: arbitrary shell (whitelist-only / full tier)

---

## Cross-refs

- AI system-prompt / condition-pack pattern mirrors `nwb-plan` (`lib/conditions/`)
- Mac executor shares Keychain conventions with other `karl-infra/services/`
- Notify webhook shared with [process-monitor](process-monitor-dashboard.md) (Discord)
- Visitor-facing directions site: go.93.fyi ([go-93fyi.md](go-93fyi.md), managed separately)

---

## Multilingual helpline (2026-05-31) — LIVE

Visitor helpline now serves **9 languages** off digits 1-9, each in a native
**ElevenLabs** voice, **pre-rendered to static MP3** (generate-once, reuse
forever — no API key or cost at call time, survives EL cancellation):

| Digit | Lang | Voice |
|-------|------|-------|
| 1 | English | George (British butler) |
| 2 | Spanish (Colombian) | Luna |
| 3 | German | Bettina |
| 4 | French | Nelly |
| 5 | Turkish | Yağmur |
| 6 | Danish | Søren |
| 7 | Korean | Totoring |
| 8 | Flemish (Vlaams) | Hans Claesen |
| 9 | Taiwanese Mandarin | Chen (speed 0.85) |

- Pipeline: `scripts/gen-voice.mjs` reads `lib/tfn/helpline-content.json` → renders
  50 files to `public/voice/<lang>/<key>.mp3` + stitched `lang_menu.mp3`. All
  loudness-normalized to -16 LUFS. Re-run with `ELEVENLABS_API_KEY=$(keychain-get
  nwb-tfn-elevenlabs-api-key) node scripts/gen-voice.mjs`.
- EL key pinned in Keychain `nwb-tfn-elevenlabs-api-key` (frictionless read).
- **Hidden backdoor moved digit 9 → `*`** (freed 9 for Mandarin). PIN gate unchanged.
- **No voicemail.** English = directions + gate + code; other 8 = directions only.
- Directions CONFIRMED by Karl 2026-05-31 (see go-93fyi.md routes). Cantonese was
  tried + dropped (no official EL support). Translations machine-assisted — flag for
  native review.
- Live-verified: static MP3s 200, signed flow plays correct per-lang audio, `*`→PIN.

## Phase status

- **Phase 0** (wire number): **live** (2026-05-31)
- **Phase A** (Vercel routes): **live** (prod deploy, signed E2E verified)
- **Phase B** (Mac executor): committed, **not loaded**
- **Phase C/E** (ElevenLabs): deferred
