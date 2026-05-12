from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row


@dataclass
class UserActivity:
    email: str
    total_workouts: int
    last_workout_at: str | None
    workouts_last_7d: int
    workouts_last_30d: int
    is_active_user: bool


# Counts + 7d/30d windows in a single query. workout_sessions.user_id is
# the user's email (per nwb-plan/db/schema.sql), so direct lookup.
_QUERY = """
SELECT
  COUNT(*)::int                                  AS total_workouts,
  MAX(started_at)::bigint                        AS last_workout_at_ms,
  COUNT(*) FILTER (
    WHERE started_at >= (extract(epoch from now() - interval '7 days') * 1000)::bigint
  )::int                                         AS workouts_last_7d,
  COUNT(*) FILTER (
    WHERE started_at >= (extract(epoch from now() - interval '30 days') * 1000)::bigint
  )::int                                         AS workouts_last_30d
FROM workout_sessions
WHERE user_id = %s
"""


async def lookup_user_activity(*, database_url: str, email: str) -> UserActivity:
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(_QUERY, (email,))
            row = await cur.fetchone() or {}

    last_ms = row.get("last_workout_at_ms")
    last_iso: str | None = None
    if last_ms:
        last_iso = datetime.fromtimestamp(
            int(last_ms) / 1000, tz=timezone.utc
        ).isoformat()

    last_30d = int(row.get("workouts_last_30d") or 0)
    return UserActivity(
        email=email,
        total_workouts=int(row.get("total_workouts") or 0),
        last_workout_at=last_iso,
        workouts_last_7d=int(row.get("workouts_last_7d") or 0),
        workouts_last_30d=last_30d,
        is_active_user=last_30d > 0,
    )
