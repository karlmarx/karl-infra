# Twilio DTMF Backdoor — phone-as-API into Karl's systems

> Call a Twilio number, authenticate, and trigger actions on the Mac Studio
> and cloud via a dialpad menu (or a spoken Jarvis-style agent). A control
> plane that survives every app/Wi-Fi/auth failure because it only needs
> *a phone — any phone*.

## Status — 2026-05-30 (DESIGN, not yet built)

- ✅ Design approved (brainstorm w/ Karl, 2026-05-30)
- ⏳ Spec → implementation plan (writing-plans next)
- ⏳ Nothing built yet

## Why

Karl has a Twilio toll-free number (TFN) whose SMS verification was rejected
(see PR #126/#129 on nwb-plan, and the decommissioned mom-93fyi-tollfree
pipeline). Voice on a TFN works fine without verification. Rather than let the
number + prepaid credits rot, repurpose it as a **voice control plane**: a
back door into Karl's own machines that works from any phone on earth.

**Why this is useful specifically:** a phone number is one of the only inputs
that works everywhere — borrowed device, hotel phone, dead laptop, locked-down
corporate phone, no app install, no Wi-Fi, no QR. A voice number with arbitrary
webhook logic is a fallback that survives almost every failure mode.

## Architecture

```
  Karl's Pixel ──dials──> +1-XXX-XXX-TFN (Twilio)
                                │ voice webhook (signed)
                                ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  VERCEL  (routes added to existing nfit.93.fyi project)        │
  │  /api/tfn-backdoor/voice     — entry: sig check, auth gate     │
  │  /api/tfn-backdoor/dispatch  — DTMF → action; KV write         │
  │  /api/tfn-backdoor/result    — async poll loop for Mac actions │
  │  /api/tfn-backdoor/tts       — ElevenLabs → Blob cache         │
  │  /api/tfn-backdoor/agent-tool— webhook the Eleven agent calls  │
  └───────────────┬───────────────────────────┬───────────────────┘
                  │                            │
        cloud action / status            Mac action (queued)
                  │                            │
                  ▼                            ▼
        (execute inline /         ┌─────────────────────────────┐
         read KV status)          │  Vercel KV (Upstash Redis)  │
                                  │  LIST  tfn:intents:pending  │
                                  │  HASH  tfn:status:current   │
                                  │  STR   tfn:result:<id>      │
                                  │  STREAM tfn:audit           │
                                  └──────────────┬──────────────┘
                                                 │ BLPOP long-poll ~5s
                                                 ▼
                          ┌──────────────────────────────────────────┐
                          │  MAC STUDIO — tfn-backdoor-agent.py       │
                          │  (launchd, persistent)                    │
                          │  - BLPOP intents, dispatch via registry   │
                          │  - actions/*.py one handler per action    │
                          │  - publish tfn:status:current every 60s   │
                          │  - every action → notify + audit          │
                          └──────────────────────────────────────────┘
```

Decisions locked in brainstorm:
- **Webhook front on Vercel, executor on Mac via KV queue** (Mac never
  publicly exposed; chosen over CF/Tailscale tunnel-into-Mac).
- **Add routes to the existing nfit.93.fyi Vercel project** (no new project).
- **Persistent launchd agent** on Mac (BLPOP long-poll, no polling cost).
- **Upstash Redis via Vercel Marketplace** for queue + status + audit.

## Components

| # | Component | Location | Purpose |
|---|---|---|---|
| 1 | `/api/tfn-backdoor/voice` | Vercel | Twilio entry. Signature verify, auth gate, returns menu TwiML |
| 2 | `/api/tfn-backdoor/dispatch` | Vercel | DTMF → action; cloud inline or KV intent write; voice confirm |
| 3 | `/api/tfn-backdoor/result` | Vercel | Poll loop for async Mac-action results (max 4 loops ≈ 8s) |
| 4 | `/api/tfn-backdoor/tts` | Vercel | ElevenLabs MP3 gen, cached in Vercel Blob (hashed by text) |
| 5 | `/api/tfn-backdoor/agent-tool` | Vercel | Webhook the Eleven agent calls during voice convo (same KV path) |
| 6 | `tfn-backdoor-agent.py` | Mac (launchd) | BLPOP loop, action registry, 60s status publisher |
| 7 | `actions/*.py` | Mac | One handler per action (restart_sync, deploy_nfit, status, …) |
| 8 | KV store | Upstash (Marketplace) | Queue + status cache + audit stream |
| 9 | Eleven agent | ElevenLabs dashboard | Claude-backed Jarvis voice agent for "press 0" branch |
| 10 | Cached prompts (MP3) | Vercel Blob | Pre-generated welcome/menu/error audio |

Reuses: existing Twilio account + rejected TFN, existing nfit.93.fyi Vercel
project, `keychain-get` secret pattern, `terminal-notifier` + Telegram notify.

## Authentication model

Two gates in order; defense in depth. **Whitelist = full access; PIN =
read-only subset.**

```
voice → ① Twilio signature verify (HMAC-SHA1, constant-time) → ② whitelist?
   ├─ From= ∈ TFN_WHITELIST → FULL menu (all digits)
   └─ else → <Gather> "Enter access code" → PIN == 9193?
              ├─ yes → SAFE menu (read-only digits only) + alert
              └─ no  → retry (max 3/call) → decoy hangup + alert
```

1. **Twilio signature** is the real security boundary — proves the request
   came from Twilio, not someone curling the Vercel endpoint. Without it the
   whole thing is an open API. HMAC-SHA1 of full URL + sorted params, keyed by
   Twilio auth token, constant-time compare. Signature fail → bare `403`.
2. **Whitelist** — `From=` E.164 ∈ `TFN_WHITELIST` env. Whitelist fail does
   NOT reveal the backdoor: plays a **decoy** ("This number is not in service")
   and hangs up.
3. **PIN fallback (`9193`)** — for non-whitelist callers (revives the
   "borrowed phone in an emergency" use case).

### PIN security posture (IMPORTANT — weak secret, bounded blast radius)

`9193` is a soft PIN: 4 digits (10⁴ brute-forceable) and semantically tied to
Karl (in his email handle). It is made acceptable by **bounding what it
unlocks**, not by strength:

- **Tiered access** — PIN callers get the **read-only safe subset only**
  (status/day/check-in). No deploys, restarts, wake, or agent. Even if `9193`
  leaks, blast radius is "a stranger hears my RAM usage," not "a stranger
  deploys my site."
- **Rate limit** — 3 PIN attempts per call → decoy hangup. 5 failed
  attempts/hour globally → PIN path disabled for 1 hour.
- **Alert on every PIN entry** (success or fail) — PIN is the lower-trust
  door, always watched. The alert + ability to rotate the TFN is the
  compensating control for whitelist-only's lack of a second factor.

Override: if Karl later wants PIN = full access (himself on a hotel phone
needing to deploy), flip the tier mapping. Default stays tiered.

## Call lifecycle & async confirmation

A phone call is synchronous; Mac execution via KV is async. Bridge:

- **Status queries** → instant. Mac pre-publishes `tfn:status:current` every
  60s; webhook reads + speaks. No wait.
- **Mac actions** → `/dispatch` writes intent, `<Redirect>`s to
  `/result?job=<id>`. `/result` checks `tfn:result:<id>`:
  - ready → speak result → menu
  - not ready → `<Pause length=2/>` + redirect to self, **max 4 loops (~8s)**
  - timeout → "Still working — I'll text you" (Mac notifies on completion)
- **Mac-offline** → if `tfn:status:current` heartbeat stale (>3 min),
  `/dispatch` warns before queueing: "Mac looks offline — queuing anyway."
  Intent persists; executes when BLPOP reconnects.

## Error handling

| Failure | Detection | Caller hears | Side effect |
|---|---|---|---|
| Bad Twilio signature | HMAC mismatch | (nothing — 403) | audit |
| Caller not whitelisted, no/bad PIN | lookup | decoy "not in service" | alert + audit |
| KV write fails | exception | "Couldn't queue that, try again" | audit + notify |
| Mac handler throws | error in `tfn:result:<id>` | "That failed — check your phone" | notify w/ traceback |
| Mac offline | stale heartbeat | "Mac offline, queued for later" | intent persists |
| ElevenLabs error/quota | non-200 | *(auto-fallback to Twilio `<Say>`)* | audit (degraded) |
| Result timeout (>8s) | 4 loops elapsed | "Still working, I'll text you" | Mac notifies later |

## Voice: Jarvis-style British butler

- **Persona** = JARVIS-*inspired* (NOT a clone of Paul Bettany — cloning a
  real identifiable person without consent violates ElevenLabs ToS and is a
  likeness-rights gray area). Achieved via **ElevenLabs Voice Design**
  (text-to-voice prompt: *"calm, refined middle-aged British man, articulate
  and measured, sophisticated AI-butler tone, subtle warmth"*) → save voice ID.
- **The character is 50% script.** All prompts written in butler register:
  formal address ("sir"), proactive status, faint dry wit, "I've taken the
  liberty of…". This lives in the prompt *text*, so it **survives the
  ElevenLabs cancellation** — degrades to "robotic butler," never "generic IVR."
- **Model tiering** (telephony is 8kHz μ-law narrowband — premium vs fast
  models converge over the wire):
  - Cached prompts (welcome/menu/error) → **Multilingual v2** (1 cr/char, paid
    once, cached in Blob forever).
  - Dynamic status readouts → **Flash v2.5** (0.5 cr/char).
  - "Press 0" agent → **Flash v2.5** (Conversational AI default, ~75ms latency).

## ElevenLabs off-ramp (first-class — Eleven WILL be cancelled)

ElevenLabs is being used **only while existing credit lasts**, then cancelled.
The off-ramp is designed in from day one as a **capability flag**, not a
feature flag.

Single source of truth: env `VOICE_PROVIDER = elevenlabs | twilio`.
All audio routes through one helper:

```
voiceResponse(text, twiml):
  if VOICE_PROVIDER == "elevenlabs" and not degraded:
      twiml.play(ttsCached(text))            # Eleven → Blob, hashed by text
  else:
      twiml.say(text, voice="Polly.Brian")   # Twilio native, free, permanent
```

Flipping to `twilio` (zero code changes):
- All prompts/results fall back to Twilio `<Say>` (robotic, free, permanent).
- "Press 0 → Claude" branch **auto-disables** (Eleven-dependent) — menu stops
  offering it, no broken SIP dials.
- Cached MP3s in Blob can be GC'd anytime.

The premium path is always an *enhancement layered over* a working free
baseline — so cancellation is a config change, not an engineering project.

## Action set (v1 digit map)

🔓 = PIN-accessible (read-only safe). 🔒 = whitelist-only.

| Key | Action | Tier | Type | Effect |
|---|---|---|---|---|
| 1 | System status | 🔓 | read | RAM free, mem pressure, MLX :8080/:8081 up?, last nfit deploy age |
| 2 | Day status | 🔓 | read | Today's PT/HEP + top `karl-todo` items (Mac→KV) |
| 3 | Restart Nextcloud sync agent | 🔒 | Mac | `launchctl kickstart -k` photo-sync agent |
| 4 | Restart photo-memory pipeline | 🔒 | Mac | re-run on-demand pipeline handler |
| 5 | Resume paused jobs | 🔒 | Mac | `SIGCONT` watchdog-paused local-batch procs |
| 6 | Deploy nfit (prod) | 🔒 | cloud | Vercel deploy hook for nfit.93.fyi |
| 7 | Send check-in ping | 🔓 | cloud | "Karl checked in" → Telegram + cld@93.fyi |
| 8 | Wake / WoL a device | 🔒 | Mac/phys | `caffeinate`-wake Mac; WoL magic packet to configured MAC |
| 9 | (reserved) | — | — | first thing Karl wishes it did after a week |
| 0 | Talk to Claude | 🔒 | agent | `<Dial><Sip>` to Eleven Jarvis agent (if `VOICE_PROVIDER=elevenlabs`) |
| * | Repeat menu | — | — | re-play menu |
| # | Goodbye | — | — | "Very good, sir." + `<Hangup/>` |

No Home Assistant detected in infra → physical/Hue deferred; revisit if Karl
has a hub.

## Cost & ElevenLabs credit ledger (~8 calls/mo, ~1.5 min each)

One-time cached prompts (Multilingual v2 @ 1 cr/char): ~600 credits (Blob,
never regenerated).

Per month:
| Item | Cost/mo |
|---|---|
| Eleven status TTS (Flash, ~200 cr/call × 8) | ~1,600 cr |
| Eleven agent minutes (~1k cr/min × ~3 min) | ~3,000 cr |
| **Eleven subtotal** | **~5,200 cr/mo** (free tier ≈ 10k → inside it) |
| Twilio TFN rental | $2.00 |
| Twilio inbound voice ($0.022/min × ~12) | ~$0.26 |
| Twilio SIP→Eleven leg | ~$0.10 |
| Vercel + Upstash | $0 (free tier) |
| **Cash/mo** | **~$2.36** |

After Eleven cancellation: cash stays ~$2.36, voice → robot-butler.

## Testing strategy

| Layer | What | Tooling |
|---|---|---|
| Unit | sig verify, whitelist match, PIN check + rate-limit/lockout, action dispatch, `voiceResponse()` both branches | vitest (Vercel), pytest (Mac) |
| Integration | signed mock Twilio POST → exact TwiML; KV intent round-trip (LPUSH→BLPOP); handler success+throw → `tfn:result` | local + Upstash test ns |
| Security | unsigned → 403; non-whitelist no-PIN → decoy; wrong PIN ×3 → hangup+alert; lockout 5/hr; PIN tier blocked from 🔒 digits | explicit cases |
| E2E/manual | real call from Pixel (whitelist) + other phone (PIN); confirm Jarvis voice, each digit, alerts | phone + Twilio console |
| Degraded | force `VOICE_PROVIDER=twilio`; full menu on `<Say>`, press-0 cleanly absent | env-flip test |

## Secrets

All via Keychain on Mac + Vercel env on cloud (never plaintext):
- `TWILIO_AUTH_TOKEN` (signature verify) — Vercel env
- `TFN_WHITELIST` — Vercel env (comma E.164)
- `TFN_PIN` = 9193 — Vercel env (so it's rotatable without redeploy of logic)
- `ELEVENLABS_API_KEY` — Vercel env; pin `nwb-elevenlabs-api-key` in Keychain on Mac
- `UPSTASH_REDIS_*` — Vercel env (Marketplace auto-provisions) + Keychain on Mac
- Vercel deploy hook URL for action 6 — Vercel env / Keychain

## Cross-refs

- [domain-93fyi.md](domain-93fyi.md) — 93.fyi zone, nfit subdomain
- [local-ai.md](local-ai.md) — MLX servers surfaced in status (action 1)
- [workout-pipeline.md](workout-pipeline.md) — PT/HEP data for day status (action 2)
- [cld-email.md](cld-email.md) — check-in ping destination (action 7)
- Decommissioned sibling: `services/_archived/mom-93fyi-tollfree/` (different TFN)

## Open questions / future

- Action 9 left open intentionally.
- Home/physical (Hue) deferred pending a hub.
- Post-Eleven: if "talk to Claude" is missed, rebuild press-0 on Twilio Media
  Streams + Claude (no Eleven dependency) — out of v1 scope.
