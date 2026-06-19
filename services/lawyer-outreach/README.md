# lawyer-outreach

Automated, personalized outreach to mass-tort law firms that may take a
Truvada/TDF PrEP injury case. Runs on the Mac under launchd, sends one
firm per cycle, watches Gmail for replies, and never re-contacts a firm
that already declined.

## Why this exists

Many firms advertise Truvada cases on SEO landing pages but have closed
intake. Manually contacting every one and tracking who replied is tedious.
This service:

1. Loads a curated registry of firms (`outreach/firms.yaml`) flagged as
   "open" / "closed" based on public statements + research.
2. For each unsent firm, generates a per-firm email via Claude using your
   real case details from `client.yaml`.
3. Sends via Gmail SMTP **or** writes a draft `.eml` to disk for review.
4. (Optional) Fills the firm's web intake form via Playwright when no
   email address is published — bails out and screenshots when it hits
   a CAPTCHA so you can finish by hand.
5. Polls Gmail every 30 min for replies from registered firms,
   classifies them (`accepted` / `declined` / `wants_info` / `unclear`),
   and updates state so you don't waste time on firms that already said no.

## Architecture

```
launchd ─every 4h─▶  scripts/run-outreach.sh ─▶ python -m outreach run
                                                       │
                                                       ├─ load firms.yaml + client.yaml
                                                       ├─ skip firms with skip:true / closed
                                                       ├─ skip firms already contacted
                                                       ├─ honor MAX_FIRMS_PER_DAY + throttle
                                                       ├─ Claude composes per-firm message
                                                       └─ send via SMTP  OR  Playwright submits form
                                                                  │
                                                                  ▼
                                                       ~/karl-infra-state/lawyer-outreach/
                                                           outreach.db   (SQLite state)
                                                           screenshots/  (form proof / CAPTCHA bailouts)
                                                           logs/         (draft .eml files)

launchd ─every 30m─▶ scripts/run-reply-scan.sh ─▶ python -m outreach scan-replies
                                                       │
                                                       └─ IMAP search per firm domain → classify → update state
```

## Setup on the Mac

### 1. Install uv (if not already)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install deps + Playwright browser

```bash
cd ~/karl-infra/services/lawyer-outreach
uv sync
uv run playwright install chromium
```

### 3. Configure secrets

```bash
cp .env.example .env
chmod 600 .env
```

Fill from KeePass:

- `ANTHROPIC_API_KEY`
- `GMAIL_APP_PASSWORD` — create at https://myaccount.google.com/apppasswords
  (2FA required). Do **not** use your Gmail account password.

### 4. Configure the client profile

```bash
cp client.example.yaml client.yaml
chmod 600 client.yaml
```

Edit `client.yaml` and replace the bracketed placeholders
(`[TRUVADA_START_YEAR]`, `[INJURY_DATE]`) with real values.

> **The runner refuses to auto-send if any placeholder is still present.**
> This is the guardrail against mass-emailing firms with `[INJURY_DATE]`
> in the body.

### 5. Verify

```bash
uv run -- python -m outreach verify
```

Should print `OK` for `client.yaml`, `firms.yaml`, and `smtp.gmail.com`.

### 6. Dry run (recommended first)

Keep `SEND_MODE=draft` in `.env`. Then:

```bash
uv run -- python -m outreach run -v
```

This writes one `.eml` file per firm under
`~/karl-infra-state/lawyer-outreach/logs/`. Open the file, sanity-check
the wording, then flip to auto.

### 7. Auto mode

Set `SEND_MODE=auto` in `.env`. Re-run:

```bash
uv run -- python -m outreach run -v
```

Each invocation contacts at most **one** firm, then exits. launchd
re-invokes on schedule. The daily cap (`MAX_FIRMS_PER_DAY=3`) and
inter-send delay (`MIN_SECONDS_BETWEEN_SENDS=900`) prevent bursts.

### 8. Install launchd jobs

```bash
cp launchd/fyi.93.lawyer-outreach.plist ~/Library/LaunchAgents/
cp launchd/fyi.93.lawyer-outreach-replies.plist ~/Library/LaunchAgents/
# Edit paths in both files to match your $HOME if not /Users/karl.

launchctl bootstrap gui/$UID ~/Library/LaunchAgents/fyi.93.lawyer-outreach.plist
launchctl enable gui/$UID/fyi.93.lawyer-outreach

launchctl bootstrap gui/$UID ~/Library/LaunchAgents/fyi.93.lawyer-outreach-replies.plist
launchctl enable gui/$UID/fyi.93.lawyer-outreach-replies
```

## CLI

```
python -m outreach run            # one outreach cycle (next eligible firm)
python -m outreach scan-replies   # poll Gmail for replies, update state
python -m outreach status         # JSON: every firm's current status
python -m outreach list-firms     # JSON: firm registry as loaded
python -m outreach verify         # smoke-test config + SMTP login
python -m outreach reset-firm <slug>   # clear state, eligible for re-contact
```

## Kill switch

Pause everything without uninstalling:

```bash
touch ~/karl-infra-state/lawyer-outreach/disable
```

Both the outreach runner and the reply scanner check for this file and
exit immediately when it exists. Delete to resume.

## How web-form CAPTCHAs are handled

Most firm intake pages embed reCAPTCHA / Cloudflare Turnstile.
The generic filler:

1. Loads the form headless in Chromium.
2. Fills visible fields by matching field name/id/placeholder/aria-label
   against a heuristic dictionary (`first_name`, `email`, `case_summary`,
   etc.).
3. Takes a full-page screenshot **before** clicking submit.
4. If a CAPTCHA is present (Turnstile or reCAPTCHA detected in the DOM,
   or `has_captcha: true` set in `firms.yaml`), the filler bails out
   without submitting and marks the firm as `form_needs_manual`. You
   open the screenshot, see what was filled, and finish the submit by
   hand in 30 seconds.
5. If no CAPTCHA, it clicks submit and screenshots the result page as
   proof.

## Updating the firm registry

The registry was populated 2026-05-13 based on web research. Firms move
in/out of intake regularly — re-run the research every 60–90 days and
update `firms.yaml`. Pay particular attention to the California Supreme
Court ruling expected in 2026 that may reopen PrEP intakes.

## Privacy / safety notes

- `client.yaml` and `.env` are gitignored. The SQLite state DB lives
  outside the repo (`~/karl-infra-state/...`).
- The composer system prompt explicitly forbids inventing dates. If
  `client.yaml` still has a `[PLACEHOLDER]`, the runner refuses to
  auto-send.
- No firm receives the same email twice — `firm_state.status` is
  checked before every send.
- The reply scanner is read-only on Gmail; it never marks messages
  read or sends from your account.
