# Hermes Agent skills

Skills for Karl's Nous Hermes Agent cloud instance (talks over Telegram).

| Skill | Schedule | What it does |
|-------|----------|--------------|
| `site-health` | every 30 min | Checks all 22 `*.93.fyi` hosts: up, public or private as expected, TLS cert valid. Messages only when something's wrong. |
| `inbox-digest` | daily 7:30am ET | Reads the last 24h of Gmail (read-only IMAP), sends a short "what needs you" digest. |

Both scripts are stdlib-only Python 3, so there's nothing to `pip install`.

## Install (on the Hermes server)

```bash
git clone https://github.com/karlmarx/karl-infra.git ~/karl-infra   # or git pull
mkdir -p ~/.hermes/skills
ln -sfn ~/karl-infra/hermes/skills/site-health  ~/.hermes/skills/site-health
ln -sfn ~/karl-infra/hermes/skills/inbox-digest ~/.hermes/skills/inbox-digest

# Smoke test
python3 ~/.hermes/skills/site-health/check_sites.py --verbose
```

Symlinks mean a `git pull` updates the skills. Restart Hermes (or start a new chat)
so it picks up the new skills.

### Gmail credentials (inbox-digest only)

1. Create a **new** Gmail app password named `hermes` at
   https://myaccount.google.com/apppasswords. Don't reuse the Mac's, so you can
   revoke this one on its own.
2. Add it to `~/.hermes/.env` on the server:
   ```
   GMAIL_USER=karlmarx9193@gmail.com
   GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
   ```
3. Test: `python3 ~/.hermes/skills/inbox-digest/fetch_inbox.py | head -30`

## Schedule (send these to Hermes in Telegram)

> Every 30 minutes, run the site-health skill. Only message me if it finds a problem.

> Every day at 7:30am America/New_York, run the inbox-digest skill and send me the digest.

Check with `/cron list` (or ask "what cron jobs do you have?").

## Notes

- `inbox-digest` is read-only (IMAP `EXAMINE` + `BODY.PEEK`). Labeling and
  archiving stay with `scripts/gmail_noise_sweep.py` on the Mac Studio, so the
  two don't fight.
- Email content gets passed to the LLM, so `SKILL.md` tells Hermes to treat it as
  untrusted data (prompt-injection guard) and never send or modify mail.
- When a site is added or goes private, update `site-health/sites.json`.
