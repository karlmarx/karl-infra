# cld@93.fyi — Claude's email identity

> Bi-directional email channel for Claude. Sends via Resend, receives via
> Cloudflare Email Routing → Gmail filter+label.

## Status — 2026-05-11

- ✅ Outbound: scaffolded, Resend key set, sender works (dry-run verified)
- ⏳ Inbound routing rule: blocked on new CF token with Email Routing scope
- ⏳ Inbox poller: stub only; needs separate Gmail API/IMAP auth (claude.ai MCP only works inside Claude Code sessions, not under launchd)
- ⏳ Gmail filter for `karlmarx9193+cld@gmail.com` → label `cld/inbox`
- ⏳ Discord webhook for notify-only path
- ⏳ First real test send

## Components

| Piece | Path | Notes |
|---|---|---|
| Unified sender | `~/karl-infra/services/email/sender.py` | Resend backend live; Gmail backend stubbed pending OAuth |
| Profiles | `~/karl-infra/services/email/profiles.json` | `cld`, `9193`, `50420`, `ben` |
| Allowlist (3c) | `~/karl-infra/services/email/allowlist.json` | Auto-reply gate |
| Inbox poller (STUB) | `~/karl-infra/services/email/inbox_poller.py` | LaunchAgent target |
| Inbox storage | `~/karl-infra/inbox/cld/` | JSON-per-thread for notify-only path |
| Slash command | `~/.claude/commands/email.md` | `/email` |
| Slash command | `~/.claude/commands/cld-triage.md` | `/cld-triage` |
| LaunchAgent | `~/Library/LaunchAgents/com.karlmarx.cld-watch.plist` | NOT loaded yet |

## DNS (already configured on the 93.fyi Cloudflare zone)

| Record | Value | Purpose |
|---|---|---|
| `93.fyi` MX | `route1/2/3.mx.cloudflare.net` | CF Email Routing receive |
| `93.fyi` TXT | `v=spf1 include:_spf.mx.cloudflare.net ~all` | SPF for inbound |
| `_dmarc.93.fyi` TXT | `v=DMARC1; p=none; rua=mailto:karlmarx9193@gmail.com` | DMARC reports |
| `resend._domainkey.93.fyi` TXT | Resend DKIM public key | Outbound DKIM |
| `send.93.fyi` MX | `feedback-smtp.us-east-1.amazonses.com` | SES bounces |
| `send.93.fyi` TXT | `v=spf1 include:amazonses.com ~all` | Outbound SPF |

All present and verified working — Resend domain was previously configured (likely during TrickAdvisor setup).

## Outstanding work (in order)

1. **CF token with Email Routing:Edit scope** — current `~/.cloudflare_api_key` is DNS:Edit only
2. **Routing rule:** `cld@93.fyi` → `karlmarx9193+cld@gmail.com`
3. **Gmail filter:** `to:karlmarx9193+cld@gmail.com` → apply label `cld/inbox`, skip Inbox
4. **First real test send** via `/email`
5. **Standalone Gmail/IMAP auth** for the poller (since claude.ai MCP is session-only)
6. **Discord webhook** for notify-only path
7. `launchctl load ~/Library/LaunchAgents/com.karlmarx.cld-watch.plist`

## Sender backends

- `--from cld` → Resend, `Claude <cld@93.fyi>` — **READY**
- `--from 9193|50420|ben` → Gmail API — **pending `gmail.send` OAuth per profile**

## Autonomy policy (option 3c — allowlist auto-reply)

- Senders in `allowlist.json:auto_reply_addresses` receive autonomous Claude replies via `/cld-triage`
- All other senders trigger a notify-only entry to `~/karl-infra/inbox/cld/<thread_id>.json` and (planned) a Discord ping
- The triage flow labels handled threads `cld/auto-replied` or `cld/needs-karl`

## Cross-references

- `~/karl-infra/infra/finflow.md` — same LaunchAgent pattern (one-shot + `StartInterval`)
- `~/karl-infra/infra/nextcloud-android-sync.md` — earlier LaunchAgent; **plaintext-pw antipattern, don't replicate**
- TrickAdvisor also uses Resend on 93.fyi for transactional email; **different API key** — blast radius is intentionally separate
