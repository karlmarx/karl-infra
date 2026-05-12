"""Gmail-over-IMAP client using an app password.

Implements the same interface as ``GmailMcp`` (``list_recent``,
``get_message``, ``apply_label``, ``create_draft``) so it's a drop-in
replacement for the MCP-based client. The factory in ``gmail.py`` picks
between the two at runtime based on which env vars are present.

Why a second implementation: the MCP path needs a Google Cloud OAuth
flow (browser, GCP project, ``gcp-oauth.keys.json``). For a single-user
mailbox, IMAP with an app password is operationally simpler and avoids
keeping a separate npm process alive per poll. The trade-off is that
labels and drafts go through Gmail's IMAP extensions instead of the
REST API.
"""

from __future__ import annotations

import asyncio
import email
import email.message
import email.utils
import imaplib
import logging
import re
from contextlib import asynccontextmanager
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import AsyncIterator

from .gmail_mcp import GmailMessage  # reuse the shared dataclass

log = logging.getLogger(__name__)


IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
ALL_MAIL = '"[Gmail]/All Mail"'
DRAFTS = '"[Gmail]/Drafts"'


def _connect(user: str, app_password: str) -> imaplib.IMAP4_SSL:
    # Strip any spaces Google's UI inserts in app passwords.
    m = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    m.login(user, app_password.replace(" ", ""))
    return m


_XGM_MSGID_RE = re.compile(rb"X-GM-MSGID (\d+)")
_XGM_THRID_RE = re.compile(rb"X-GM-THRID (\d+)")


def _extract_gm_id(raw: bytes, pat: re.Pattern[bytes]) -> str:
    m = pat.search(raw)
    return m.group(1).decode() if m else ""


def _decode_h(value: str | None) -> str:
    """Decode RFC 2047-encoded header (e.g. =?utf-8?q?foo?=) to plain text."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _decode_part(part: email.message.Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        # Prefer text/plain over text/html
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.is_multipart():
                return _decode_part(part)
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.is_multipart():
                # Cheap HTML strip — agent only needs readable text
                text = _decode_part(part)
                return re.sub(r"<[^>]+>", " ", text)
        return ""
    return _decode_part(msg)


class GmailImap:
    """IMAP-backed Gmail client. Same interface as GmailMcp."""

    def __init__(self, m: imaplib.IMAP4_SSL, user: str) -> None:
        self._m = m
        self._user = user

    async def init(self) -> None:
        # Parity with GmailMcp.init(); IMAP login already happened.
        return None

    # ---- public API ----------------------------------------------------

    async def list_recent(
        self, sender_allowlist: list[str], max_results: int = 10
    ) -> list[dict[str, str]]:
        from_q = " OR ".join(f"from:{s}" for s in sender_allowlist)
        query = f"({from_q}) -label:triaged newer_than:1d"
        return await asyncio.to_thread(self._list_recent_sync, query, max_results)

    async def get_message(self, message_id: str) -> GmailMessage:
        return await asyncio.to_thread(self._get_message_sync, message_id)

    async def apply_label(self, message_id: str, label_name: str) -> None:
        await asyncio.to_thread(self._apply_label_sync, message_id, label_name)

    async def create_draft(self, message: GmailMessage, body_text: str) -> str:
        return await asyncio.to_thread(self._create_draft_sync, message, body_text)

    # ---- sync implementations (called via to_thread) -------------------

    def _list_recent_sync(self, query: str, max_results: int) -> list[dict[str, str]]:
        self._m.select("INBOX", readonly=False)
        typ, data = self._m.uid(
            "SEARCH", None, "X-GM-RAW", f'"{query}"'
        )  # type: ignore[arg-type]
        if typ != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()[-max_results:]
        results: list[dict[str, str]] = []
        for uid in uids:
            typ, fetched = self._m.uid("FETCH", uid, "(X-GM-MSGID X-GM-THRID)")
            if typ != "OK" or not fetched:
                continue
            raw = fetched[0] if isinstance(fetched[0], bytes) else b""
            if isinstance(fetched[0], tuple):
                raw = fetched[0][0]
            msgid = _extract_gm_id(raw, _XGM_MSGID_RE)
            thrid = _extract_gm_id(raw, _XGM_THRID_RE)
            if msgid:
                results.append({"id": msgid, "thread_id": thrid})
        return results

    def _select_all_mail(self) -> None:
        # Some accounts localize the folder name; if "All Mail" select fails,
        # fall back to a LIST + match on \All flag.
        typ, _ = self._m.select(ALL_MAIL, readonly=False)
        if typ != "OK":
            typ, folders = self._m.list()
            for line in folders or []:
                if isinstance(line, bytes) and b"\\All" in line:
                    name = line.rsplit(b'"/" ', 1)[-1].strip().decode()
                    self._m.select(name, readonly=False)
                    return

    def _find_uid_by_msgid(self, message_id: str) -> bytes | None:
        self._select_all_mail()
        typ, data = self._m.uid("SEARCH", None, "X-GM-MSGID", message_id)
        if typ != "OK" or not data or not data[0]:
            return None
        return data[0].split()[0]

    def _get_message_sync(self, message_id: str) -> GmailMessage:
        uid = self._find_uid_by_msgid(message_id)
        if not uid:
            raise RuntimeError(f"message {message_id} not found in All Mail")
        typ, data = self._m.uid("FETCH", uid, "(RFC822 X-GM-THRID)")
        if typ != "OK" or not data:
            raise RuntimeError(f"FETCH failed for {message_id}")

        raw_msg = b""
        thrid = ""
        for item in data:
            if isinstance(item, tuple):
                meta = item[0] if isinstance(item[0], bytes) else b""
                thrid = _extract_gm_id(meta, _XGM_THRID_RE) or thrid
                raw_msg = item[1] if isinstance(item[1], bytes) else raw_msg

        msg = email.message_from_bytes(raw_msg)
        subject = _decode_h(msg.get("Subject")) or "(no subject)"
        from_addr = _decode_h(msg.get("From"))
        to = _decode_h(msg.get("To"))
        body = _extract_body(msg)
        date_ms = 0
        date_h = msg.get("Date")
        if date_h:
            try:
                date_ms = int(
                    email.utils.parsedate_to_datetime(date_h).timestamp() * 1000
                )
            except (TypeError, ValueError):
                pass
        snippet = re.sub(r"\s+", " ", body)[:200] if body else ""
        return GmailMessage(
            id=message_id,
            thread_id=thrid,
            from_addr=from_addr,
            to=to,
            subject=subject,
            snippet=snippet,
            body=body,
            date_ms=date_ms,
        )

    def _apply_label_sync(self, message_id: str, label_name: str) -> None:
        uid = self._find_uid_by_msgid(message_id)
        if not uid:
            raise RuntimeError(f"message {message_id} not found")
        # Gmail auto-creates labels on STORE if they don't exist.
        # Wrap label name in quotes; double up internal quotes.
        escaped = label_name.replace('"', '\\"')
        typ, _ = self._m.uid(
            "STORE", uid, "+X-GM-LABELS", f'("{escaped}")'
        )  # type: ignore[arg-type]
        if typ != "OK":
            raise RuntimeError(f"STORE +X-GM-LABELS failed: {typ}")

    def _create_draft_sync(self, message: GmailMessage, body_text: str) -> str:
        draft = MIMEText(body_text, "plain", "utf-8")
        draft["To"] = message.from_addr
        draft["From"] = self._user
        draft["Subject"] = f"Re: {message.subject}"
        draft["Date"] = formatdate(localtime=True)
        domain = self._user.split("@", 1)[1] if "@" in self._user else "local"
        draft["Message-ID"] = make_msgid(domain=domain)
        if message.id:
            # Help Gmail thread the draft with the original
            draft["In-Reply-To"] = f"<gmail-msgid-{message.id}@{domain}>"
            draft["References"] = f"<gmail-msgid-{message.id}@{domain}>"

        raw = draft.as_bytes()
        typ, _ = self._m.append(DRAFTS, "(\\Draft)", None, raw)
        if typ != "OK":
            raise RuntimeError(f"APPEND to Drafts failed: {typ}")
        # IMAP APPEND doesn't return a server-side draft id; return a synthetic
        # one keyed off the source message so logs stay correlatable.
        return f"imap-draft-{message.id}"


@asynccontextmanager
async def connect_gmail_imap(
    user: str, app_password: str
) -> AsyncIterator[GmailImap]:
    m = await asyncio.to_thread(_connect, user, app_password)
    try:
        client = GmailImap(m, user)
        await client.init()
        yield client
    finally:
        try:
            await asyncio.to_thread(m.logout)
        except Exception:
            pass
