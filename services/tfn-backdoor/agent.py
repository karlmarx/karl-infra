#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["redis", "requests"]
# ///
"""Twilio DTMF backdoor — Mac executor.

Blocks on the intent queue, runs handlers, writes results, and republishes the
status snapshot every ~60s (driven by the BLPOP timeout).
"""
from __future__ import annotations

import logging
import time

import handlers  # noqa: F401 — registers handlers as a side effect
import kv
from notify import notify
from registry import dispatch
from status import build_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tfn.agent")

STATUS_INTERVAL = 60.0


def main() -> None:
    r = kv.client()
    log.info("tfn-backdoor agent up; publishing status + draining %s", kv.PENDING)
    kv.publish_status(r, build_status())
    last_status = time.time()

    while True:
        item = r.blpop(kv.PENDING, timeout=5)
        if item is not None:
            _, raw = item
            try:
                intent = kv.Intent.from_json(raw)
            except Exception:
                log.exception("bad intent payload: %s", raw)
                continue
            log.info("dispatch %s (id=%s)", intent.action, intent.id)
            speech = dispatch(intent.action, intent)
            ok = "failed" not in speech.lower()
            kv.write_result(r, intent.id, "ok" if ok else "error", speech)
            kv.audit(r, {"event": "exec", "action": intent.action, "ok": ok})
            notify(f"{intent.action}: {speech}")

        if time.time() - last_status >= STATUS_INTERVAL:
            try:
                kv.publish_status(r, build_status())
            except Exception:
                log.exception("status publish failed")
            last_status = time.time()


if __name__ == "__main__":
    main()
