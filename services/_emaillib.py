"""Shared SMTP helper for Karl's local digest/alert pipelines.

Lives outside the individual digest scripts so adding new email pipelines
(watchdog alerts, weekly best-of, on-this-day) doesn't duplicate the SMTP
config or the placeholder-guard logic.

Reads GMAIL_USER / GMAIL_APP_PASSWORD / DIGEST_TO from env. Each LaunchAgent
plist sets these in EnvironmentVariables.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = os.environ.get("GMAIL_USER", "karlmarx9193@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
DIGEST_TO = os.environ.get("DIGEST_TO", "karlmarx9193@gmail.com")
PLACEHOLDER = "FILL_IN_FROM_KEEPASS"


def password_configured() -> bool:
    return bool(GMAIL_APP_PASSWORD) and GMAIL_APP_PASSWORD != PLACEHOLDER


def send(
    subject: str,
    plain: str,
    html: str | None = None,
    inline_images: dict[str, bytes] | None = None,
    to: str | None = None,
    image_subtype: str = "jpeg",
) -> tuple[bool, str]:
    """Send via Gmail SMTP_SSL.

    inline_images: cid -> bytes. Reference in HTML as <img src="cid:foo">.
    image_subtype: MIME subtype for inline images — "jpeg" (default), "gif",
        "png". All inline_images in one call share the same subtype; use
        per-image MIMEImage construction if you need to mix.
    Returns (ok, message).
    """
    if not password_configured():
        return False, "GMAIL_APP_PASSWORD not configured"

    recipient = to or DIGEST_TO
    msg = MIMEMultipart("related" if inline_images else "alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = recipient
    msg["Subject"] = subject

    if inline_images:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(plain, "plain"))
        if html:
            alt.attach(MIMEText(html, "html"))
        msg.attach(alt)
        ext = {"jpeg": "jpg", "gif": "gif", "png": "png"}.get(image_subtype, image_subtype)
        for cid, data in inline_images.items():
            # Python 3.13+ removed imghdr; MIMEImage's auto-detect breaks —
            # always pass _subtype explicitly.
            img = MIMEImage(data, _subtype=image_subtype)
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=f"{cid}.{ext}")
            msg.attach(img)
    else:
        msg.attach(MIMEText(plain, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, [recipient], msg.as_string())
        return True, f"sent to {recipient}"
    except Exception as e:
        return False, f"smtp error: {e!r}"
