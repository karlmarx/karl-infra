#!/usr/bin/env python3
"""Dump recent Gmail inbox messages as JSON for the inbox-digest skill.

Read-only: the mailbox is opened with EXAMINE and bodies are fetched with
BODY.PEEK, so nothing gets marked read, labeled, or moved.

Credentials: GMAIL_USER / GMAIL_APP_PASSWORD from the environment, falling
back to ~/.hermes/.env. Use a Gmail app password, not your real password.

Run:  python3 fetch_inbox.py [--days 1] [--max 60]
"""

import argparse
import email
import email.policy
import html
import imaplib
import json
import os
import re
import sys
from pathlib import Path

ENV_PATH = Path.home() / ".hermes/.env"
SNIPPET_CHARS = 800

# Skip what gmail_noise_sweep.py already labels, plus Gmail's own promo tabs.
SEARCH = (
    "in:inbox newer_than:{days}d -label:SMS -label:Noise/Promos "
    "-label:Noise/Newsletters -category:promotions -category:social"
)


def load_creds() -> tuple[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    env.update({k: v for k, v in os.environ.items() if v})
    user, password = env.get("GMAIL_USER"), env.get("GMAIL_APP_PASSWORD")
    if not (user and password):
        sys.exit("Missing GMAIL_USER / GMAIL_APP_PASSWORD (env or ~/.hermes/.env)")
    return user, password


def body_text(msg: email.message.EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    text = part.get_content()
    if part.get_content_type() == "text/html":
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()[:SNIPPET_CHARS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--max", type=int, default=60)
    args = ap.parse_args()

    user, password = load_creds()
    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(user, password)
    m.select("INBOX", readonly=True)  # EXAMINE

    query = SEARCH.format(days=args.days)
    _, data = m.uid("SEARCH", "X-GM-RAW", f'"{query}"')
    uids = data[0].split()[-args.max :]

    out = []
    for uid in reversed(uids):  # newest first
        _, parts = m.uid("FETCH", uid, "(X-GM-THRID BODY.PEEK[])")
        raw = next(p[1] for p in parts if isinstance(p, tuple))
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        out.append(
            {
                "from": str(msg["From"] or ""),
                "subject": str(msg["Subject"] or ""),
                "date": str(msg["Date"] or ""),
                "snippet": body_text(msg),
            }
        )
    m.logout()
    print(json.dumps({"query": query, "count": len(out), "messages": out}, indent=1))


if __name__ == "__main__":
    main()
