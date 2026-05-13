#!/usr/bin/env python3
"""Unified email sender.

Dispatches to Resend (cld@93.fyi) or Gmail (personal accounts) by --from profile.

Secrets sourced from environment (~/.secrets):
  RESEND_API_KEY              for the Resend backend
  GMAIL_OAUTH_<profile>       for the Gmail backend (pending OAuth wiring)

Usage:
  source ~/.secrets
  python3 sender.py --from cld --to alice@example.com --subject "Hi" --body "Hello!"
  python3 sender.py --from cld --to alice@example.com --subject "Hi" --dry-run < body.txt

Threading:
  --in-reply-to <Message-ID>  Sets In-Reply-To + References headers
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent
PROFILES_FILE = SERVICE_DIR / "profiles.json"


def load_profiles() -> dict:
    return json.loads(PROFILES_FILE.read_text())


def send_resend(profile: dict, *, to: list[str], subject: str, body_text: str,
                body_html: str | None = None, reply_to: str | None = None,
                in_reply_to: str | None = None, dry_run: bool = False) -> dict:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        sys.exit("RESEND_API_KEY not set. Run `source ~/.secrets` first.")

    payload: dict = {
        "from": profile["from"],
        "to": to,
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html
    if reply_to or profile.get("reply_to"):
        payload["reply_to"] = reply_to or profile["reply_to"]
    if in_reply_to:
        payload["headers"] = {
            "In-Reply-To": in_reply_to,
            "References": in_reply_to,
        }

    if dry_run:
        return {"dry_run": True, "payload": payload}

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "karl-infra-mailer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"Resend API error {e.code}: {body}")


def send_gmail(profile: dict, **kwargs) -> dict:
    sys.exit(
        f"Gmail backend not yet wired for profile '{profile.get('name')}'.\n"
        "Required: (1) install google-api-python-client + google-auth-oauthlib,\n"
        "          (2) run the gmail.send OAuth flow (see README.md),\n"
        f"          (3) drop the token at {profile.get('oauth_token_path')}"
    )


BACKENDS = {
    "resend": send_resend,
    "gmail": send_gmail,
}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Send email via unified profile-based sender.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--from", dest="from_", default="cld",
                   help="Profile: cld (default) | 9193 | 50420 | ben")
    p.add_argument("--to", required=True, action="append",
                   help="Recipient address (repeatable for multiple)")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", help="Plain-text body. If omitted, reads from stdin.")
    p.add_argument("--html", help="Optional HTML body")
    p.add_argument("--reply-to", help="Override profile default reply-to")
    p.add_argument("--in-reply-to", help="Original Message-ID (for threading)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print payload without sending")
    args = p.parse_args()

    profiles = load_profiles()
    if args.from_ not in profiles:
        sys.exit(f"Unknown profile '{args.from_}'. Known: {sorted(profiles)}")

    profile = dict(profiles[args.from_], name=args.from_)

    body_text = args.body if args.body is not None else sys.stdin.read()
    if not body_text.strip():
        sys.exit("Body is empty (pass --body or pipe content to stdin)")

    backend = BACKENDS.get(profile.get("backend"))
    if backend is None:
        sys.exit(f"Unknown backend '{profile.get('backend')}'")

    result = backend(
        profile,
        to=args.to,
        subject=args.subject,
        body_text=body_text,
        body_html=args.html,
        reply_to=args.reply_to,
        in_reply_to=args.in_reply_to,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("DRY RUN — would have sent:")
        print(json.dumps(result["payload"], indent=2))
    else:
        print(f"Sent. id={result.get('id', '?')} via {profile['backend']} as {profile['from']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
