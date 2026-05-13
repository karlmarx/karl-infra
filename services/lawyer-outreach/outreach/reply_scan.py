from __future__ import annotations

import email
import email.policy
import imaplib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .models import Firm
from .state import State

log = logging.getLogger(__name__)


DECLINE_PATTERNS = [
    r"unable to (?:assist|help|take|represent)",
    r"not able to (?:assist|help|take|represent)",
    r"(?:we|our (?:firm|office)) (?:are|is) not (?:accepting|pursuing|taking)",
    r"(?:after (?:careful )?review|after (?:reviewing|evaluating))",
    r"decline(?:d|s)? (?:your|to take|representation)",
    r"will not be (?:able to )?(?:proceed|move forward|represent)",
    r"do(?:es)? not meet (?:our|the) criteria",
    r"statute of limitations",
    r"prep (?:cases?|claims?) (?:are )?not (?:accepted|being accepted)",
]

ACCEPT_PATTERNS = [
    r"(?:we|our (?:firm|office)) (?:would like|are interested|want)",
    r"(?:please|kindly) (?:complete|sign|fill|review|execute).{0,40}(?:retainer|engagement|intake|contract)",
    r"thank you for (?:choosing|retaining|hiring)",
    r"welcome (?:to|aboard|email)",
]

INFO_REQUEST_PATTERNS = [
    r"(?:please|can you|could you) (?:send|provide|share)",
    r"medical records",
    r"(?:more|additional) information",
    r"questionnaire",
    r"intake form",
    r"call (?:us|me|the office)",
]


@dataclass
class Reply:
    sender: str
    subject: str
    body: str
    thread_id: str
    message_id: str
    received_at: datetime


def classify(body: str) -> str:
    text = body.lower()
    if any(re.search(p, text) for p in DECLINE_PATTERNS):
        return "declined"
    if any(re.search(p, text) for p in ACCEPT_PATTERNS):
        return "accepted"
    if any(re.search(p, text) for p in INFO_REQUEST_PATTERNS):
        return "wants_info"
    return "unclear"


def scan_replies(
    *,
    gmail_user: str,
    gmail_app_password: str,
    firms: list[Firm],
    state: State,
    lookback_days: int = 14,
) -> list[tuple[str, str]]:
    """Scan Gmail INBOX for replies from any firm's intake_email.

    Returns a list of (firm_slug, classification) tuples for newly recorded
    replies. Idempotent on Message-ID.
    """
    domain_to_slug: dict[str, str] = {}
    addr_to_slug: dict[str, str] = {}
    for f in firms:
        if f.intake_email:
            addr_to_slug[f.intake_email.lower()] = f.slug
            domain = f.intake_email.split("@", 1)[-1].lower()
            domain_to_slug[domain] = f.slug

    if not addr_to_slug:
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%d-%b-%Y")
    new_replies: list[tuple[str, str]] = []

    with imaplib.IMAP4_SSL("imap.gmail.com") as m:
        m.login(gmail_user, gmail_app_password)
        m.select("INBOX")

        for addr, slug in addr_to_slug.items():
            typ, data = m.search(None, f'(SINCE {since} FROM "{addr}")')
            if typ != "OK":
                continue
            for uid in (data[0] or b"").split():
                typ, msg_data = m.fetch(uid, "(RFC822)")
                if typ != "OK" or not msg_data:
                    continue
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                if not raw:
                    continue
                msg = email.message_from_bytes(raw, policy=email.policy.default)
                message_id = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
                if not message_id:
                    continue
                sender = msg.get("From", "")
                subject = msg.get("Subject", "")
                body = _plain_body(msg)
                thread_id = (msg.get("Thread-Id") or msg.get("X-GM-THRID") or "").strip()
                classification = classify(body)
                inserted = state.record_reply(
                    firm_slug=slug,
                    sender=sender,
                    subject=subject,
                    classification=classification,
                    snippet=body[:500],
                    thread_id=thread_id or None,
                    message_id=message_id,
                )
                if inserted:
                    log.info("recorded reply firm=%s class=%s subject=%r", slug, classification, subject)
                    new_replies.append((slug, classification))
                    if classification == "declined":
                        state.set_firm_status(slug, "declined", channel="reply", notes=f"auto-classified decline: {subject}")
                    elif classification == "accepted":
                        state.set_firm_status(slug, "accepted", channel="reply", notes=f"auto-classified accept: {subject}")
                    elif classification == "wants_info":
                        state.set_firm_status(slug, "reply_received", channel="reply", notes=f"info-request: {subject}")
    return new_replies


def _plain_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_content()
                except Exception:
                    continue
    else:
        try:
            return msg.get_content()
        except Exception:
            return ""
    return ""
