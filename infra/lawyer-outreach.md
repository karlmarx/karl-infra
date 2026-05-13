# lawyer-outreach

Mac Studio launchd service. Personalized outreach + intake automation for
Truvada/TDF PrEP mass-tort firms.

- **Repo path**: `services/lawyer-outreach/`
- **Runtime**: Python 3.11+ (`uv`) + Playwright Chromium
- **Schedule**: outreach every 4 h; reply scan every 30 min
- **State**: `~/karl-infra-state/lawyer-outreach/outreach.db` (SQLite, WAL)
- **Screenshots / drafts**: `~/karl-infra-state/lawyer-outreach/{screenshots,logs}/`
- **Kill switch**: `~/karl-infra-state/lawyer-outreach/disable` (touch to pause)
- **Logs**: `~/Library/Logs/lawyer-outreach.{log,err}`

## Why it exists

Truvada/TDF intake is winding down across mass-tort firms (federal MDL on
appeal, California JCCP awaiting CA Supreme Court ruling). Most firms that
advertise the case have actually closed intake. The service maintains a
curated registry (`outreach/firms.yaml`) flagged "open" vs "closed",
contacts only open firms, and never re-contacts firms that decline.

## What's automated

| Action | How |
|--------|-----|
| Per-firm message generation | Claude Opus 4.7 with strict no-fabrication system prompt; refuses to fill bracketed placeholders |
| Email send | Gmail SMTP via app password (2FA-protected) |
| Web-form fill | Playwright Chromium, heuristic field matching, full-page screenshots before submit |
| CAPTCHA handling | Detect Turnstile / reCAPTCHA / hCaptcha in DOM, bail out, screenshot, mark `form_needs_manual` |
| Reply triage | IMAP poll per firm domain; regex-classify accepted / declined / wants_info / unclear; update `firm_state.status` |
| Daily cap | `MAX_FIRMS_PER_DAY=3` (env); enforced in SQLite `budget` table |
| Inter-send throttle | `MIN_SECONDS_BETWEEN_SENDS=900` |
| Placeholder gate | Auto-send refuses if `client.yaml` still contains `[INJURY_DATE]` / `[TRUVADA_START_YEAR]` |
| Idempotency | `firm_state` and `replies.message_id UNIQUE` |

## Registry (2026-05-13)

**Open intake (8 firms)**: chalik-chalik (FL), parafinczuk-wolf (FL), ben-crump (FL),
torhoerman, hollis-law, showard-law, lieff-cabraser.

**Closed (skipped)**: levin-papantonio, johnson-becker, sokolove, ward-black,
miller-zois, awko-law, wisner-baum, baron-budd, wagstaff-cartmell.

See `services/lawyer-outreach/outreach/firms.yaml` for full details
including evidence quotes and source URLs.

## Re-research cadence

The registry should be refreshed every 60-90 days; firms move in and out
of intake as the litigation evolves. Pending CA Supreme Court ruling
expected 2026 may reopen PrEP intakes.
