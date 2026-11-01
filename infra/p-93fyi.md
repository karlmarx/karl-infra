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

## Setup checklist

- [ ] GitHub secrets `TWILIO_AUTH_TOKEN`, `COURTS_OWNER_TOKEN`, `ELEVENLABS_API_KEY`
- [ ] Merge where-93fyi PR → deploy
- [ ] Cloudflare Access app `p.93.fyi` with Bypass / Everyone
- [ ] Email Routing `p@93.fyi` → Worker `p-93fyi`
- [ ] Run *Render court phone prompts* workflow
- [ ] Vercel `tfn-93fyi`: `PICKLEBALL_VOICE_URL=https://p.93.fyi/twilio/voice`; merge tfn PR
- [ ] Twilio number: messaging webhook → `https://p.93.fyi/twilio/sms`
- [ ] Resubmit toll-free verification (website p.93.fyi, terms p.93.fyi/terms); texts out blocked until approved
- [ ] Verify: `curl -sS -o /dev/null -w "%{http_code}" https://p.93.fyi/` → 200
- [ ] Merge 93-fyi PR (launcher tile) once live

## Open

- where phone + watch apps: reporting UI (API ready: `POST /api/report`).
- Translations (es, pt-BR) are machine-assisted; get a native read.
- The tfn WhatsApp face still gives directions, if its sender was ever registered.
