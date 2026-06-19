from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS firm_state (
    firm_slug TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    last_channel TEXT,
    last_attempt_at TEXT,
    next_eligible_at TEXT,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firm_slug TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    status TEXT NOT NULL,
    subject TEXT,
    message_excerpt TEXT,
    message_id TEXT,
    draft_id TEXT,
    form_screenshot_path TEXT,
    detail_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_attempts_firm ON attempts(firm_slug);
CREATE INDEX IF NOT EXISTS idx_attempts_sent_at ON attempts(sent_at);

CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firm_slug TEXT NOT NULL,
    received_at TEXT NOT NULL,
    sender TEXT NOT NULL,
    subject TEXT,
    classification TEXT NOT NULL,
    snippet TEXT,
    thread_id TEXT,
    message_id TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_replies_firm ON replies(firm_slug);

CREATE TABLE IF NOT EXISTS budget (
    day TEXT PRIMARY KEY,
    sends_count INTEGER NOT NULL DEFAULT 0,
    spend_usd REAL NOT NULL DEFAULT 0.0
);
"""


@dataclass
class Attempt:
    firm_slug: str
    channel: str
    sent_at: str
    status: str
    subject: str | None = None
    message_excerpt: str | None = None
    message_id: str | None = None
    draft_id: str | None = None
    form_screenshot_path: str | None = None
    detail: dict | None = None


class State:
    """SQLite-backed tracker for outreach attempts."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
        finally:
            conn.close()

    def get_firm_status(self, slug: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM firm_state WHERE firm_slug = ?", (slug,)
            ).fetchone()
        return dict(row) if row else None

    def set_firm_status(
        self,
        slug: str,
        status: str,
        channel: str | None = None,
        last_error: str | None = None,
        notes: str | None = None,
    ) -> None:
        now = _iso_now()
        with self._conn() as c:
            existing = c.execute(
                "SELECT error_count FROM firm_state WHERE firm_slug = ?", (slug,)
            ).fetchone()
            error_count = (existing["error_count"] if existing else 0)
            if last_error:
                error_count += 1
            c.execute(
                """
                INSERT INTO firm_state(firm_slug, status, last_channel, last_attempt_at, error_count, last_error, notes)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(firm_slug) DO UPDATE SET
                    status = excluded.status,
                    last_channel = COALESCE(excluded.last_channel, firm_state.last_channel),
                    last_attempt_at = excluded.last_attempt_at,
                    error_count = excluded.error_count,
                    last_error = COALESCE(excluded.last_error, firm_state.last_error),
                    notes = COALESCE(excluded.notes, firm_state.notes)
                """,
                (slug, status, channel, now, error_count, last_error, notes),
            )

    def record_attempt(self, attempt: Attempt) -> int:
        with self._conn() as c:
            cur = c.execute(
                """
                INSERT INTO attempts(
                    firm_slug, channel, sent_at, status, subject,
                    message_excerpt, message_id, draft_id, form_screenshot_path,
                    detail_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.firm_slug,
                    attempt.channel,
                    attempt.sent_at,
                    attempt.status,
                    attempt.subject,
                    attempt.message_excerpt,
                    attempt.message_id,
                    attempt.draft_id,
                    attempt.form_screenshot_path,
                    json.dumps(attempt.detail) if attempt.detail else None,
                ),
            )
            return int(cur.lastrowid or 0)

    def record_reply(
        self,
        firm_slug: str,
        sender: str,
        subject: str | None,
        classification: str,
        snippet: str | None,
        thread_id: str | None,
        message_id: str,
    ) -> bool:
        """Idempotent: returns True if newly inserted, False if seen before."""
        with self._conn() as c:
            try:
                c.execute(
                    """
                    INSERT INTO replies(firm_slug, received_at, sender, subject, classification, snippet, thread_id, message_id)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        firm_slug,
                        _iso_now(),
                        sender,
                        subject,
                        classification,
                        snippet,
                        thread_id,
                        message_id,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def sends_today(self) -> int:
        day = _today()
        with self._conn() as c:
            row = c.execute("SELECT sends_count FROM budget WHERE day = ?", (day,)).fetchone()
            return int(row["sends_count"]) if row else 0

    def charge_send(self, dollars: float = 0.0) -> None:
        day = _today()
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO budget(day, sends_count, spend_usd) VALUES(?, 1, ?)
                ON CONFLICT(day) DO UPDATE SET
                    sends_count = sends_count + 1,
                    spend_usd = spend_usd + excluded.spend_usd
                """,
                (day, dollars),
            )

    def last_send_at(self) -> datetime | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT sent_at FROM attempts WHERE status IN ('sent','submitted','drafted') ORDER BY sent_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            return datetime.fromisoformat(row["sent_at"])

    def firms_not_yet_contacted(self, all_slugs: list[str]) -> list[str]:
        with self._conn() as c:
            seen = {
                r["firm_slug"]
                for r in c.execute(
                    "SELECT firm_slug FROM firm_state WHERE status NOT IN ('not_contacted','error')"
                ).fetchall()
            }
        return [s for s in all_slugs if s not in seen]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()
