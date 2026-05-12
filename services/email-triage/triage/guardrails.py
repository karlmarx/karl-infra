from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Config
from .supabase_store import Budget, Store


@dataclass
class PreflightResult:
    ok: bool
    reason: str | None
    budget: Budget


def preflight(cfg: Config, store: Store) -> PreflightResult:
    budget = store.get_budget()
    if budget.spent_usd >= cfg.daily_budget_usd:
        return PreflightResult(
            False,
            f"daily ${cfg.daily_budget_usd:.2f} cap hit (${budget.spent_usd:.4f})",
            budget,
        )
    if budget.triage_count >= cfg.max_triages_per_day:
        return PreflightResult(
            False,
            f"daily {cfg.max_triages_per_day} triage count hit",
            budget,
        )
    return PreflightResult(True, None, budget)


_ADDR_RE = re.compile(r"<([^>]+)>")


def extract_address(from_header: str) -> str:
    m = _ADDR_RE.search(from_header)
    return (m.group(1) if m else from_header).strip().lower()


def sender_allowed(cfg: Config, from_header: str) -> bool:
    return extract_address(from_header) in cfg.sender_allowlist
