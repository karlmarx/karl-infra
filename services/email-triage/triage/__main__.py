from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .config import load_config
from .poll import run_poll
from .supabase_store import Store


def main() -> int:
    parser = argparse.ArgumentParser(prog="triage")
    parser.add_argument(
        "--env", type=Path, default=None, help="Path to .env file (default: ./.env)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="DEBUG-level logging"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("poll", help="Run one poll+triage cycle")
    sub.add_parser("status", help="Print current budget + recent activity")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    cfg = load_config(env_file=args.env)
    store = Store(cfg.supabase_url, cfg.supabase_service_role_key)

    if args.cmd == "poll":
        stats = asyncio.run(run_poll(cfg, store))
        print(json.dumps(stats, indent=2))
        return 0

    if args.cmd == "status":
        budget = store.get_budget()
        print(json.dumps({
            "budget": {
                "date": budget.date,
                "spent_usd": budget.spent_usd,
                "triage_count": budget.triage_count,
                "daily_cap_usd": cfg.daily_budget_usd,
                "daily_count_cap": cfg.max_triages_per_day,
            },
            "model": cfg.model,
            "allowlist": cfg.sender_allowlist,
        }, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
