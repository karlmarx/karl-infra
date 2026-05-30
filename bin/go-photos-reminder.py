#!/usr/bin/env python3
"""Hourly email nag (2026-05-31 only) reminding Karl to shoot the go.93.fyi photos.

Fired by launchd `com.kmx.go-photos-reminder` (StartCalendarInterval pinned to
May 31, hours 6-20). Sends via Gmail SMTP using GMAIL_USER / GMAIL_APP_PASSWORD
from the plist env — same mechanism as services/_emaillib.py.

Auto-stops when EITHER:
  * the sentinel file exists, OR
  * a "series of stills" (>= 2 media files) newer than 2026-05-31 00:00 has
    landed in ~/Documents (i.e. Karl dropped the photos in).
On stop it writes the sentinel and sends one short confirmation, so the
remaining hourly fires that day go quiet. The job never fires past May 31.
"""
from __future__ import annotations

import datetime
import os
import pathlib
import smtplib
from email.mime.text import MIMEText

HOME = pathlib.Path.home()
SENTINEL = HOME / "Library/Application Support/go-93fyi/photos-done"
DOCS = HOME / "Documents"
THRESHOLD = datetime.datetime(2026, 5, 31, 0, 0, 0).timestamp()

USER = os.environ.get("GMAIL_USER", "karlmarx9193@gmail.com")
PW = os.environ.get("GMAIL_APP_PASSWORD", "")
TO = os.environ.get("DIGEST_TO", "karlmarx9193@gmail.com")

MEDIA_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov")

REMINDER = """Today's the day to capture the missing shots for your apartment-directions site (https://go.93.fyi). When you're out, please grab:

1) A CLEAR shot of THE building (3000 / East Park Square) -- plus an overhead/aerial view if you can.
2) Indoor foot route: clubhouse -> past the big table -> turn right -> through the green push-to-exit door -> past the mailboxes -> right -> left -> elevator -> floor 5 -> Apt 501.
3) Both ButterflyMX boxes (driving gate box + clubhouse box) + the code-entry keypad.
4) The WRONG entrance behind Sprouts (so the site can show "not this one").

Drop them in ~/Documents and these reminders stop automatically. They also stop on their own after today.
-- Claude
"""

DONE_MSG = """Looks like you dropped the photos into ~/Documents -- the hourly reminders will stop now. I'll wire the real shots into go.93.fyi.
-- Claude
"""


def send(subject: str, body: str) -> None:
    if not PW:
        print("no GMAIL_APP_PASSWORD in env; skipping")
        return
    msg = MIMEText(body, "plain")
    msg["From"] = USER
    msg["To"] = TO
    msg["Subject"] = subject
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(USER, PW)
            s.sendmail(USER, [TO], msg.as_string())
        print(f"sent: {subject}")
    except Exception as e:  # noqa: BLE001
        print(f"smtp error: {e!r}")


def new_media_count() -> int:
    n = 0
    try:
        for f in DOCS.iterdir():
            if f.suffix.lower() in MEDIA_EXTS:
                try:
                    if f.stat().st_mtime >= THRESHOLD:
                        n += 1
                except OSError:
                    pass
    except OSError:
        pass
    return n


def main() -> None:
    if SENTINEL.exists():
        print("sentinel present; done")
        return
    if new_media_count() >= 2:
        SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL.write_text("done\n")
        send("\U0001F389 go.93.fyi shots -- got 'em, thanks!", DONE_MSG)
        return
    send("\U0001F4F8 go.93.fyi -- grab those photos/videos today", REMINDER)


if __name__ == "__main__":
    main()
