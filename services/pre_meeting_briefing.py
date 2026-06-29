#!/usr/bin/env python3
"""Pre-meeting briefing — 10-20 min before each Calendar event, email a digest.

Reads upcoming events from a Google Calendar private iCal URL (no OAuth needed).
For each attendee, IMAPs Gmail for recent threads. Optionally calls local
:8081 mlx-vlm to synthesize a one-line "Likely topics" hint.

Schedule via launchd every 5 min. State file dedups so each event briefs only
once per day.

Setup (one-time):
  1. Google Calendar → Settings → [your calendar] → "Integrate calendar"
  2. Copy the "Secret address in iCal format" URL
  3. Write to ~/.config/karl-infra/calendar-ical-url (single line, mode 600)
  4. launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kmx.pre-meeting-briefing.plist
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["icalendar", "requests", "openai"]
# ///

from __future__ import annotations

import imaplib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path

import requests
from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

CONFIG_DIR = Path.home() / ".config/karl-infra"
ICAL_URL_FILE = CONFIG_DIR / "calendar-ical-url"
STATE_FILE = Path.home() / ".local/share/pre-meeting-briefing/state.json"
LOOKAHEAD_MIN = 20  # window start
LOOKAHEAD_MAX = 10  # window end (i.e. briefing fires 10–20 min before event)
GMAIL_LOOKBACK_DAYS = 30
MAX_THREADS_PER_ATTENDEE = 3
MLX_BASE = os.environ.get("MLX_VLM_BASE", "http://localhost:8081/v1").rstrip("/")
IMAP_HOST = "imap.gmail.com"

GMAIL_USER = os.environ.get("GMAIL_USER", "karlmarx9193@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def get_ical_url() -> str | None:
    """Read URL from config file, env, or return None."""
    env = os.environ.get("CALENDAR_ICAL_URL")
    if env:
        return env.strip()
    if ICAL_URL_FILE.exists():
        url = ICAL_URL_FILE.read_text().strip()
        if url and url.startswith("http"):
            return url
    return None


def fetch_upcoming_events(url: str) -> list[dict]:
    """Return events starting in the LOOKAHEAD_MAX..LOOKAHEAD_MIN window."""
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=LOOKAHEAD_MAX)
    window_end = now + timedelta(minutes=LOOKAHEAD_MIN)

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)

    matches = []
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        start = comp.get("DTSTART")
        if not start:
            continue
        dt = start.dt
        if not isinstance(dt, datetime):  # all-day events skipped
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if not (window_start <= dt <= window_end):
            continue

        attendees = []
        for raw in comp.get("ATTENDEE", []) if isinstance(comp.get("ATTENDEE"), list) else [comp.get("ATTENDEE")] if comp.get("ATTENDEE") else []:
            try:
                # ATTENDEE values look like mailto:foo@bar.com; the param CN= holds the name
                addr = str(raw).removeprefix("mailto:")
                name = raw.params.get("CN", "") if hasattr(raw, "params") else ""
                if addr and addr.lower() != GMAIL_USER.lower():
                    attendees.append({"email": addr, "name": str(name) or addr})
            except Exception:
                continue

        matches.append({
            "uid": str(comp.get("UID", f"{dt.isoformat()}")),
            "start": dt,
            "end": comp.get("DTEND").dt if comp.get("DTEND") else None,
            "summary": str(comp.get("SUMMARY", "(untitled)")),
            "location": str(comp.get("LOCATION", "")),
            "description": str(comp.get("DESCRIPTION", "")),
            "attendees": attendees,
            "organizer": str(comp.get("ORGANIZER", "")).removeprefix("mailto:"),
        })

    return matches


def decode_header_str(raw: str) -> str:
    """Decode RFC 2047 encoded-word headers (=?utf-8?b?...?=) to plain text."""
    if not raw:
        return ""
    parts = decode_header(raw)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(enc or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def search_gmail_threads(imap: imaplib.IMAP4_SSL, address: str, since: datetime) -> list[dict]:
    """Return last MAX_THREADS_PER_ATTENDEE messages exchanged with `address`."""
    date_str = since.strftime("%d-%b-%Y")
    # Search FROM or TO that address since the cutoff date
    typ, data = imap.search(None, f'(OR (FROM "{address}") (TO "{address}")) SINCE {date_str}')
    if typ != "OK" or not data or not data[0]:
        return []

    ids = data[0].split()
    # Latest first
    ids = ids[-MAX_THREADS_PER_ATTENDEE:][::-1]

    results = []
    for msg_id in ids:
        typ, msg_data = imap.fetch(msg_id, "(RFC822.HEADER BODY.PEEK[TEXT])")
        if typ != "OK" or not msg_data:
            continue
        # msg_data is a list of tuples; the first tuple's [1] holds the bytes
        raw_bytes = b""
        for part in msg_data:
            if isinstance(part, tuple) and len(part) >= 2:
                raw_bytes += part[1]
        if not raw_bytes:
            continue
        msg = message_from_bytes(raw_bytes)
        subject = decode_header_str(msg.get("Subject", ""))
        from_addr = parseaddr(msg.get("From", ""))[1]
        date = msg.get("Date", "")
        # Get a snippet of body text
        body_snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True) or b""
                    body_snippet = body.decode("utf-8", errors="replace")[:240].strip()
                    break
        else:
            body = msg.get_payload(decode=True) or b""
            body_snippet = body.decode("utf-8", errors="replace")[:240].strip()
        results.append({
            "subject": subject,
            "from": from_addr,
            "date": date,
            "snippet": re.sub(r"\s+", " ", body_snippet)[:200],
        })
    return results


def summarize_likely_topics(event: dict, threads_by_attendee: dict[str, list[dict]]) -> str | None:
    """One-line synthesis via local :8081 9B. Returns None on any failure."""
    try:
        from openai import OpenAI
    except ImportError:
        return None

    subjects = []
    for attendee, threads in threads_by_attendee.items():
        for t in threads[:2]:
            subjects.append(f"{attendee}: {t['subject']}")
    if not subjects:
        return None

    prompt = (
        f"Meeting: {event['summary']}\n"
        f"Recent email subjects with attendees:\n"
        + "\n".join(f"  - {s}" for s in subjects[:8])
        + "\n\nIn one short line (<25 words), what is this meeting most likely to cover?"
    )
    try:
        client = OpenAI(base_url=MLX_BASE, api_key="mlx-vlm")
        resp = client.chat.completions.create(
            model="mlx-community/Qwen3.5-9B-MLX-4bit",
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
            timeout=15,
        )
        out = resp.choices[0].message.content.strip()
        return out.splitlines()[0][:200] if out else None
    except Exception:
        return None


def render_briefing(event: dict, threads_by_attendee: dict[str, list[dict]], likely_topics: str | None) -> tuple[str, str]:
    start_local = event["start"].astimezone()
    end_local = event["end"].astimezone() if event["end"] else None
    time_range = start_local.strftime("%H:%M")
    if end_local:
        time_range += f"→{end_local.strftime('%H:%M')}"
    minutes_until = int((event["start"] - datetime.now(timezone.utc)).total_seconds() / 60)

    plain_lines = [
        f"📅 Briefing in {minutes_until} min · {time_range}",
        "",
        f"{event['summary']}",
    ]
    if event["location"]:
        plain_lines.append(f"📍 {event['location']}")
    plain_lines.append("")

    html_lines = [
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:680px;margin:1.5rem auto;line-height:1.5'>",
        f"<div style='color:#888;font-size:13px;margin-bottom:0.5rem'>"
        f"📅 Briefing in {minutes_until} min · {time_range}</div>",
        f"<h2 style='margin-top:0;color:#333'>{event['summary']}</h2>",
    ]
    if event["location"]:
        html_lines.append(f"<p style='color:#666'>📍 {event['location']}</p>")

    if likely_topics:
        plain_lines.extend(["Likely topics (mlx-9B synthesis):", f"  {likely_topics}", ""])
        html_lines.append(
            f"<div style='background:#fafafa;border-left:3px solid #4CAF50;"
            f"padding:0.75rem 1rem;margin:1rem 0;font-size:14px'>"
            f"<strong>Likely topics:</strong> {likely_topics}</div>"
        )

    if event["attendees"]:
        plain_lines.append(f"Attendees ({len(event['attendees'])}):")
        html_lines.append("<h3 style='color:#555;margin-top:1.5rem'>Attendees</h3>")
        for a in event["attendees"]:
            label = f"{a['name']} <{a['email']}>" if a["name"] != a["email"] else a["email"]
            plain_lines.append(f"  - {label}")
            html_lines.append(f"<div style='font-size:14px'><strong>{a['name']}</strong> &lt;{a['email']}&gt;</div>")
            threads = threads_by_attendee.get(a["email"], [])
            if not threads:
                plain_lines.append("    (no recent email)")
                html_lines.append("<p style='color:#999;font-size:13px;margin:0 0 0.5rem 1rem'>(no recent email)</p>")
            for t in threads:
                plain_lines.append(f"    · {t['subject']} ({t['date'][:16]})")
                if t["snippet"]:
                    plain_lines.append(f"      > {t['snippet'][:120]}")
                html_lines.append(
                    f"<div style='margin:0.25rem 0 0.5rem 1rem;font-size:13px'>"
                    f"<div style='color:#555'>· {t['subject']} "
                    f"<span style='color:#999'>({t['date'][:16]})</span></div>"
                    f"<div style='color:#777;margin-left:1rem;font-style:italic'>{t['snippet'][:200]}</div>"
                    f"</div>"
                )
        plain_lines.append("")
    else:
        plain_lines.append("(no attendees in calendar event)")
        html_lines.append("<p style='color:#999;font-style:italic'>(no attendees in calendar event)</p>")

    plain_lines.append("—")
    plain_lines.append("Generated by ~/karl-infra/services/pre_meeting_briefing.py")
    html_lines.append(
        "<p style='color:#888;font-size:11px;margin-top:2rem;border-top:1px solid #eee;padding-top:0.5rem'>"
        "Generated by ~/karl-infra/services/pre_meeting_briefing.py</p>"
        "</body></html>"
    )

    return "\n".join(plain_lines), "".join(html_lines)


def main() -> int:
    now = datetime.now(timezone.utc)
    url = get_ical_url()
    if not url:
        print(f"[{datetime.now():%H:%M:%S}] no iCal URL configured at {ICAL_URL_FILE} (set it once; see script docstring)")
        return 0

    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD == "FILL_IN_FROM_KEEPASS":
        print(f"[{datetime.now():%H:%M:%S}] GMAIL_APP_PASSWORD not configured")
        return 0

    try:
        events = fetch_upcoming_events(url)
    except Exception as e:
        print(f"[{datetime.now():%H:%M:%S}] iCal fetch failed: {e!r}")
        return 1

    if not events:
        print(f"[{datetime.now():%H:%M:%S}] no events in {LOOKAHEAD_MAX}-{LOOKAHEAD_MIN}min window")
        return 0

    state = load_state()
    briefed = set(state.get("briefed", []))
    # Daily cleanup — drop briefed events older than 24h
    state["briefed"] = [b for b in briefed if b.startswith(now.strftime("%Y-%m-%d"))]
    briefed = set(state["briefed"])

    for event in events:
        key = f"{now.strftime('%Y-%m-%d')}::{event['uid']}"
        if key in briefed:
            print(f"  already briefed: {event['summary']}")
            continue

        threads_by_attendee: dict[str, list[dict]] = {}
        if event["attendees"]:
            try:
                with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
                    imap.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                    imap.select("INBOX", readonly=True)
                    since = now - timedelta(days=GMAIL_LOOKBACK_DAYS)
                    for a in event["attendees"]:
                        threads_by_attendee[a["email"]] = search_gmail_threads(imap, a["email"], since)
                    imap.logout()
            except Exception as e:
                print(f"  IMAP failed: {e!r}")

        likely = summarize_likely_topics(event, threads_by_attendee)
        plain, html = render_briefing(event, threads_by_attendee, likely)

        start_local = event["start"].astimezone()
        subject = f"📅 {event['summary']} · {start_local:%H:%M}"
        ok, info = send_email(subject, plain, html)
        print(f"  briefing for '{event['summary']}': email {'✓' if ok else '✗'} {info}")
        if ok:
            briefed.add(key)

    state["briefed"] = sorted(briefed)
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
