from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import load_config
from .firms import load_firms, load_client
from .runner import run_outreach, run_reply_scan
from .state import State


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="outreach")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--env", type=Path, default=None, help="path to .env file")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run", help="run one outreach cycle (process next eligible firm)")
    sub.add_parser("scan-replies", help="poll Gmail for replies from firms in registry")
    sub.add_parser("status", help="print current state of all firms")
    sub.add_parser("list-firms", help="print firm registry as JSON")
    sub.add_parser("verify", help="validate config + client.yaml + firms.yaml + can reach SMTP")

    p_send = sub.add_parser("send-one", help="force-send to a specific firm (debug)")
    p_send.add_argument("firm_slug")

    p_reset = sub.add_parser("reset-firm", help="clear state for a single firm so it's eligible again")
    p_reset.add_argument("firm_slug")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    cfg = load_config(args.env)

    if args.cmd == "run":
        n = run_outreach(cfg)
        print(f"sent_or_drafted={n}")
        return 0

    if args.cmd == "scan-replies":
        n = run_reply_scan(cfg)
        print(f"new_replies={n}")
        return 0

    if args.cmd == "status":
        state = State(cfg.state_db)
        firms = load_firms(cfg.firms_yaml)
        rows = []
        for f in firms:
            st = state.get_firm_status(f.slug) or {}
            rows.append({
                "slug": f.slug,
                "name": f.name,
                "intake_email": f.intake_email,
                "status": st.get("status", "not_contacted"),
                "last_attempt_at": st.get("last_attempt_at"),
                "last_error": st.get("last_error"),
            })
        print(json.dumps(rows, indent=2))
        return 0

    if args.cmd == "list-firms":
        firms = load_firms(cfg.firms_yaml)
        print(json.dumps([f.__dict__ for f in firms], indent=2))
        return 0

    if args.cmd == "verify":
        problems: list[str] = []
        try:
            load_client(cfg.client_yaml)
            print("client.yaml: OK")
        except Exception as e:
            problems.append(f"client.yaml: {e}")
            print(f"client.yaml: FAIL — {e}")
        try:
            firms = load_firms(cfg.firms_yaml)
            print(f"firms.yaml: OK ({len(firms)} firms)")
        except Exception as e:
            problems.append(f"firms.yaml: {e}")
            print(f"firms.yaml: FAIL — {e}")
        # SMTP login probe
        try:
            import smtplib, ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.login(cfg.gmail_user, cfg.gmail_app_password)
            print("smtp.gmail.com: OK")
        except Exception as e:
            problems.append(f"smtp: {e}")
            print(f"smtp.gmail.com: FAIL — {e}")
        return 0 if not problems else 1

    if args.cmd == "send-one":
        # Future: take a firm_slug, force-send. Left as TODO; for now run().
        print("send-one not yet implemented; use `run` and reset state if needed", file=sys.stderr)
        return 2

    if args.cmd == "reset-firm":
        import sqlite3
        with sqlite3.connect(cfg.state_db) as c:
            c.execute("DELETE FROM firm_state WHERE firm_slug = ?", (args.firm_slug,))
        print(f"reset firm: {args.firm_slug}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
