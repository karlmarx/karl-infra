from __future__ import annotations

import logging
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

log = logging.getLogger(__name__)


def send_email(
    *,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    gmail_user: str,
    gmail_app_password: str,
    from_name: str,
    reply_to: str,
    to_addr: str,
    subject: str,
    body: str,
) -> str:
    """Send a plain-text email via Gmail SMTP. Returns RFC 822 Message-ID."""
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, gmail_user))
    msg["To"] = to_addr
    msg["Reply-To"] = reply_to or gmail_user
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    message_id = make_msgid(domain="lawyer-outreach.local")
    msg["Message-ID"] = message_id
    # Custom header to make replies easy to attribute back to this run.
    msg["X-Outreach-Trace"] = uuid.uuid4().hex
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.login(gmail_user, gmail_app_password)
        s.send_message(msg)

    log.info("sent email to %s subject=%r", to_addr, subject)
    return message_id
