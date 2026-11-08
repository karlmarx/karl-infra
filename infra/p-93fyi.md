# p.93.fyi — pickleball court counts

Self-reported counts (playing, waiting, Hagen challenge vs 4-on-4-off,
wet/damp/dry) for **Hagen Park** and **Wimberly Fields**, reported by text,
phone call, email, or the where apps. Public board at https://p.93.fyi.

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/where-93fyi](https://github.com/karlmarx/where-93fyi), `courts/` (full design + privacy notes in `courts/README.md`) |
| **Worker** | `p-93fyi` (account `f1ccbe18…`), custom domain `p.93.fyi` |
| **State** | one SQLite-backed Durable Object `CourtsStore` (reporters + reports) |
| **Deploy** | `.github/workflows/deploy-courts.yml` on push to `main` touching `courts/` |
| **Voice prompts** | `.github/workflows/courts-voice.yml` (manual) renders ElevenLabs MP3s, commits, redeploys |
| **Phone/text** | Twilio toll-free +1 888 601-6132: voice via tfn.93.fyi `<Redirect>` (flag `PICKLEBALL_VOICE_URL`), SMS webhook `https://p.93.fyi/twilio/sms` |
| **Email** | Cloudflare Email Routing `p@93.fyi` → Worker `p-93fyi` |
| **Issue** | karlmarx/where-93fyi#15 |
| **Created** | 2026-11-01 |

## Sensitive data

No phone number or email address is stored: reporter ids are HMAC-SHA256 keyed
with the Worker secret `ID_HASH_KEY` (generated once by the deploy workflow,
never printed). Twilio's own logs still hold numbers.

## Secrets

| Secret | Where | Purpose |
|---|---|---|
| `TWILIO_AUTH_TOKEN` | GitHub secret → Worker | verify `X-Twilio-Signature` |
| `COURTS_OWNER_TOKEN` | GitHub secret → Worker `OWNER_TOKEN` | `/admin` and where-app reports |
| `ID_HASH_KEY` | Worker only (auto-created) | reporter id HMAC key |
| `ELEVENLABS_API_KEY` | GitHub secret | voice render workflow only |
| `GOOGLE_CLIENT_ID` | GitHub secret → Worker | Sign in with Google (Web client, JS origin `https://p.93.fyi`, no secret) |
| `RESEND_API_KEY` | GitHub secret → Worker | email sign-in links from p@93.fyi (added 2026-11-01) |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET` | GitHub secret → Worker (optional) | bot check on anonymous web reports |

## Setup checklist

- [ ] GitHub secrets `TWILIO_AUTH_TOKEN`, `COURTS_OWNER_TOKEN` (= where app token), `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_ID`; `RESEND_API_KEY` ✅
- [ ] Merge where-93fyi PR → deploy
- [ ] Cloudflare Access app `p.93.fyi` with Bypass / Everyone
- [ ] Email Routing `p@93.fyi` → Worker `p-93fyi`
- [ ] Run *Render court phone prompts* workflow
- [ ] Vercel `tfn-93fyi`: `PICKLEBALL_VOICE_URL=https://p.93.fyi/twilio/voice`; merge tfn PR
- [ ] Twilio number: messaging webhook → `https://p.93.fyi/twilio/sms`
- [ ] Resubmit toll-free verification (website p.93.fyi, terms p.93.fyi/terms); texts out blocked until approved
- [ ] Verify: `curl -sS -o /dev/null -w "%{http_code}" https://p.93.fyi/` → 200
- [ ] Sign in on p.93.fyi with Google, then `/admin` → "Make my signed-in account the owner"
- [ ] Print `/sign/hagen` and `/sign/wimberly` (ask the park before posting)
- [ ] Merge 93-fyi PR (launcher tile) once live

## Web features (2026-11-01)

Map board with face pins, QR quick report `/r/<park>`, printable signs, Google +
email-link sign-in, owner tier (wins 45 min), check-ins with per-player
visibility, owner-approved avatars and court photos (stored in the DO, EXIF
stripped in the browser). where apps: "Courts" launcher entry on phone + watch.

## Open

- Phase B ideas: web push alerts ("Hagen under 8 waiting", "Karl started playing"), busiest-hours history, owner announcements, "need a 4th".
- Translations (es, pt-BR) are machine-assisted; get a native read.
- The tfn WhatsApp face still gives directions, if its sender was ever registered.

## PicklePeek rebrand (2026-11-07)

`/` = PicklePeek board with an Old/New/Side-by-side switch (`?ui=`) and demo scenarios; old board at `/classic`.
Footer links `karl@picklepeek.com` (feedback) and Instagram `@picklepeek`: both still to be set up.
