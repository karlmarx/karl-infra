#!/usr/bin/env python3
"""Gmail noise sweep: label + archive auto-forwarded SMS, promos, newsletters.

Uses Gmail IMAP with the app password from email-triage/.env.
Labels are created via IMAP CREATE (become real Gmail labels);
labeling via X-GM-LABELS; archiving = delete-from-INBOX (+expunge),
which removes the INBOX label only — messages stay in All Mail.

Run:  uv run ~/karl-infra/scripts/gmail_noise_sweep.py [--dry-run]
"""

import imaplib
import sys
from pathlib import Path

ENV_PATH = Path.home() / "karl-infra/services/email-triage/.env"

# --- Rules ---------------------------------------------------------------
# Auto-forwarded SMS: self-sent with subject "SMS from ..."
SMS_LABEL = "SMS"

PROMO_LABEL = "Noise/Promos"
PROMO_SENDERS = [
    "hello@e.lululemon.com",
    "jcrew@mail.jcrew.com",
    "bombas@hello.bombas.com",
    "reply@goodr.com",
    "uber@uber.com",  # marketing only; receipts come from noreply@uber.com
    "no-reply@messages.doordash.com",
    "marketing@email.irobot.com",
    "worldofhyatt@loyalty.hyatt.com",
    "no-reply@email.point.me",
    "fandango@movies.fandango.com",
    "support@peachymen.com",
    "no-reply@ohsnap.com",
    "support@magneticbagcompany.com",
    "vivobarefoot@newsletter.vivobarefoot.com",
    "support@kumorico.com",
    "contact@unit1gear.com",
    "no-reply@exact.publix.com",
    "announcements@email.broadwayacrossamerica.com",
    "newsletters@e.trekbikes.com",
    "info@spinwavepickleball.com",
    "postmaster@email.mr-s-leather.com",
    "blast@mail.fresha.com",
    "info@pb.dupr.com",
    "noreply@tapmango.com",
    "noreply@email.browardcenter.org",
    "teachers@liforme.com",
    "squaremktg.com",  # domain match — rotating + addresses
]

NEWS_LABEL = "Noise/Newsletters"
NEWS_SENDERS = [
    "noreply@md.getsentry.com",
    "hello@news.railway.app",
    "ship@info.vercel.com",
    "hello@ollama.com",
    "enewsletters@moody.senate.gov",
    "jeremy@builtwithscience.com",
]


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env


def ensure_label(m: imaplib.IMAP4_SSL, name: str) -> None:
    typ, _ = m.create(f'"{name}"')
    # 'NO' with ALREADYEXISTS is fine


def sweep(m: imaplib.IMAP4_SSL, search: str, label: str, dry: bool) -> int:
    """Search INBOX, apply label, mark read, archive. Skips \\Flagged (starred)."""
    typ, data = m.uid("SEARCH", None, search)
    uids = data[0].split() if data and data[0] else []
    if not uids:
        return 0
    # skip starred messages
    keep = []
    for uid in uids:
        typ, fdata = m.uid("FETCH", uid, "(FLAGS)")
        if fdata and fdata[0] and b"\\Flagged" in fdata[0]:
            continue
        keep.append(uid)
    if not keep:
        return 0
    uidset = b",".join(keep).decode()
    if dry:
        print(f"  would label+archive {len(keep)} msgs -> {label}")
        return len(keep)
    m.uid("STORE", uidset, "+X-GM-LABELS", f'("{label}")')
    m.uid("STORE", uidset, "+FLAGS", r"(\Seen \Deleted)")
    m.expunge()
    return len(keep)


def main() -> None:
    dry = "--dry-run" in sys.argv
    env = load_env(ENV_PATH)
    user, pw = env["GMAIL_USER"], env["GMAIL_APP_PASSWORD"]

    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(user, pw)

    for label in (SMS_LABEL, PROMO_LABEL, NEWS_LABEL):
        ensure_label(m, label)

    m.select("INBOX")
    total = 0

    # 1. Auto-forwarded SMS (self-sent, "SMS from" subject)
    n = sweep(m, f'(FROM "{user}" SUBJECT "SMS from")', SMS_LABEL, dry)
    print(f"SMS forwards: {n}")
    total += n

    # 2. Promo senders
    for s in PROMO_SENDERS:
        n = sweep(m, f'(FROM "{s}")', PROMO_LABEL, dry)
        if n:
            print(f"Promo {s}: {n}")
        total += n

    # 3. Newsletter senders
    for s in NEWS_SENDERS:
        n = sweep(m, f'(FROM "{s}")', NEWS_LABEL, dry)
        if n:
            print(f"Newsletter {s}: {n}")
        total += n

    print(f"TOTAL {'would be ' if dry else ''}cleaned: {total}")
    m.close()
    m.logout()


if __name__ == "__main__":
    main()
