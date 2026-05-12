from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from supabase import Client, create_client

log = logging.getLogger(__name__)


@dataclass
class ActivityEvent:
    kind: str
    email_id: str | None = None
    from_addr: str | None = None
    subject: str | None = None
    tool_name: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    cost_usd: float | None = None


@dataclass
class Budget:
    date: str
    spent_usd: float
    triage_count: int


class Store:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.client: Client = create_client(url, service_role_key)

    @staticmethod
    def today_utc() -> str:
        return dt.datetime.now(dt.timezone.utc).date().isoformat()

    def log_event(self, ev: ActivityEvent) -> None:
        row = {
            "kind": ev.kind,
            "email_id": ev.email_id,
            "from_addr": ev.from_addr,
            "subject": ev.subject,
            "tool_name": ev.tool_name,
            "payload": ev.payload,
            "cost_usd": ev.cost_usd,
        }
        try:
            self.client.table("triage_events").insert(row).execute()
        except Exception:
            log.exception("failed to insert triage_event")

    def get_budget(self, date: str | None = None) -> Budget:
        date = date or self.today_utc()
        res = (
            self.client.table("triage_budget")
            .select("*")
            .eq("date", date)
            .maybe_single()
            .execute()
        )
        if res and res.data:
            return Budget(
                date=res.data["date"],
                spent_usd=float(res.data["spent_usd"]),
                triage_count=int(res.data["triage_count"]),
            )
        return Budget(date=date, spent_usd=0.0, triage_count=0)

    def charge_budget(self, cost_usd: float) -> Budget:
        date = self.today_utc()
        res = self.client.rpc(
            "charge_triage_budget", {"p_date": date, "p_cost": cost_usd}
        ).execute()
        row = res.data[0] if isinstance(res.data, list) and res.data else res.data
        return Budget(
            date=date,
            spent_usd=float(row["spent_usd"]),
            triage_count=int(row["triage_count"]),
        )

    def is_processed(self, email_id: str) -> bool:
        res = (
            self.client.table("triage_processed")
            .select("email_id")
            .eq("email_id", email_id)
            .maybe_single()
            .execute()
        )
        return bool(res and res.data)

    def mark_processed(self, email_id: str) -> None:
        try:
            self.client.table("triage_processed").upsert(
                {"email_id": email_id}, on_conflict="email_id"
            ).execute()
        except Exception:
            log.exception("failed to upsert triage_processed")
