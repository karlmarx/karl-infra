# email/ — unified email service

Sends from any of Karl's configured profiles. Currently wired:

| Profile | Backend | Identity | Status |
|---------|---------|----------|--------|
| `cld`   | Resend  | `Claude <cld@93.fyi>` | READY |
| `9193`  | Gmail   | `karlmarx9193@gmail.com` | Needs `gmail.send` OAuth |
| `50420` | Gmail   | `5042021062karlmarx@gmail.com` | Needs `gmail.send` OAuth |
| `ben`   | Gmail   | `benjaminwages@gmail.com` | Needs `gmail.send` OAuth |

## Send

```bash
source ~/.secrets
python3 sender.py --from cld --to alice@example.com --subject "Hi" --body "Hello"
```

Add `--dry-run` to preview payload without sending.

## Slash commands

- `/email` — send mail
- `/cld-triage` — process cld@93.fyi inbox per the option-3c allowlist

## Gmail OAuth (when ready)

To enable a Gmail profile:

```bash
# Once per profile:
uv run python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    '~/karl-infra/services/email/oauth/client_secret.json',
    ['https://www.googleapis.com/auth/gmail.send'],
)
creds = flow.run_local_server(port=0)
with open('oauth/<profile>.json', 'w') as f:
    f.write(creds.to_json())
"
```

You'll need a GCP project with Gmail API enabled and a desktop OAuth client.

## Files

- `sender.py` — entry point
- `profiles.json` — profile configs
- `allowlist.json` — auto-reply gating for `cld@93.fyi`
- `inbox_poller.py` — LaunchAgent target (stub)
- `oauth/` — per-profile Gmail tokens (gitignore)

See `~/karl-infra/infra/cld-email.md` for the full system doc.
