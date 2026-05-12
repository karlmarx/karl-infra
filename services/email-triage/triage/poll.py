from __future__ import annotations

import logging

from .agent import triage_email
from .config import Config
from .gmail_mcp import GmailMcp, connect_gmail_mcp
from .guardrails import preflight, sender_allowed
from .supabase_store import ActivityEvent, Store

log = logging.getLogger(__name__)


async def run_poll(cfg: Config, store: Store) -> dict[str, int]:
    stats = {"scanned": 0, "triaged": 0, "skipped_processed": 0, "skipped_sender": 0}

    pre = preflight(cfg, store)
    if not pre.ok:
        store.log_event(
            ActivityEvent(kind="budget.exceeded", payload={"reason": pre.reason})
        )
        log.info("preflight failed: %s", pre.reason)
        return stats

    store.log_event(ActivityEvent(kind="poll.start"))

    async with connect_gmail_mcp(cfg.gmail_mcp_command, cfg.gmail_mcp_args) as gmail:
        refs = await gmail.list_recent(cfg.sender_allowlist, max_results=10)
        stats["scanned"] = len(refs)

        for ref in refs:
            email_id = ref["id"]
            if not email_id:
                continue
            if store.is_processed(email_id):
                stats["skipped_processed"] += 1
                continue

            msg = await gmail.get_message(email_id)
            if not sender_allowed(cfg, msg.from_addr):
                store.log_event(
                    ActivityEvent(
                        kind="poll.skip",
                        email_id=msg.id,
                        from_addr=msg.from_addr,
                        subject=msg.subject,
                        payload={"reason": "sender not in allowlist"},
                    )
                )
                store.mark_processed(email_id)
                stats["skipped_sender"] += 1
                continue

            store.log_event(
                ActivityEvent(
                    kind="poll.match",
                    email_id=msg.id,
                    from_addr=msg.from_addr,
                    subject=msg.subject,
                )
            )

            try:
                await triage_email(cfg, store, gmail, msg)
                stats["triaged"] += 1
            except Exception as e:
                log.exception("triage failed for %s", email_id)
                store.log_event(
                    ActivityEvent(
                        kind="triage.error",
                        email_id=email_id,
                        payload={"error": str(e)},
                    )
                )
            store.mark_processed(email_id)

            after = preflight(cfg, store)
            if not after.ok:
                store.log_event(
                    ActivityEvent(
                        kind="budget.exceeded",
                        payload={"reason": after.reason, "stopping_batch": True},
                    )
                )
                break

    return stats
