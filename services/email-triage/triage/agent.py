from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import (
    Message,
    MessageParam,
    TextBlockParam,
    ToolResultBlockParam,
    ToolUseBlock,
)

from .config import Config
from .gmail_mcp import GmailMcp, GmailMessage
from .supabase_store import ActivityEvent, Store
from .tools import TOOL_PARAMS, ToolRunner

log = logging.getLogger(__name__)


# Pricing per 1M tokens. Update when model pricing changes.
# Keys are model id prefixes (longest-first matching).
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7": {
        "input": 15.0,
        "output": 75.0,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4-5": {
        "input": 1.0,
        "output": 5.0,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
}


def estimate_cost_usd(model: str, usage: dict[str, int]) -> float:
    prices = None
    for prefix, p in PRICING.items():
        if model.startswith(prefix):
            prices = p
            break
    if prices is None:
        prices = PRICING["claude-opus-4-7"]  # safe upper bound

    return (
        usage.get("input_tokens", 0) / 1_000_000 * prices["input"]
        + usage.get("output_tokens", 0) / 1_000_000 * prices["output"]
        + usage.get("cache_creation_input_tokens", 0)
        / 1_000_000
        * prices["cache_write"]
        + usage.get("cache_read_input_tokens", 0) / 1_000_000 * prices["cache_read"]
    )


SYSTEM_PROMPT = """You are an email triage agent for Karl.

For each email you receive, you MUST:
1. Decide a tier: urgent | normal | low | bug | spam
2. Call gmail_apply_label exactly once with "triaged/<tier>"
3. If action is needed by Karl, call todoist_create_task
4. If it's a bug report or code-related, call github_create_issue
5. If a personal reply is warranted, call gmail_draft_reply (drafts are safe, not sent)
6. If TRULY urgent (time-sensitive, blocking, financial), call twilio_send_urgent_sms ONCE with <=160 chars
7. Call finish_triage exactly once at the end with a 1-sentence summary and the tier

DIAGNOSTIC TOOLS (call these BEFORE filing issues / sending SMS when relevant):
- github_recent_merges: when the email reports something broken or regressed,
  call this for the suspect repo FIRST. Include suspect PRs in the github_create_issue
  body as "Recent merges that may be related", and reference the most likely
  culprit by PR number in any twilio_send_urgent_sms.
- lookup_nwbfit_user_activity: when the email mentions a specific user account
  problem on NWB Fit (an email address appears in the body), call this first.
  Use last_workout_at and workouts_last_7d / workouts_last_30d to gauge severity
  (active power user = higher priority; lapsed account = lower). Include the
  result in the github_create_issue body.

Be decisive. Use a maximum of 8 tool calls before finish_triage. Don't call any
tool more than once per triage. For pure notifications, receipts, or marketing
email, just label and finish — no diagnostics, no task, no draft, no SMS."""


@dataclass
class TriageResult:
    ok: bool
    tier: str | None
    summary: str | None
    iterations: int
    usage: dict[str, int]
    cost_usd: float
    stopped: str | None = None


def _format_email(m: GmailMessage) -> str:
    body = m.body if len(m.body) <= 6000 else m.body[:6000] + "\n…[truncated]"
    return (
        "Email to triage:\n"
        f"From: {m.from_addr}\n"
        f"To: {m.to}\n"
        f"Subject: {m.subject}\n"
        f"Message-Id: {m.id}\n"
        f"Thread-Id: {m.thread_id}\n"
        "\n--- BODY ---\n"
        f"{body or m.snippet}\n"
        "--- END BODY ---"
    )


async def triage_email(
    cfg: Config,
    store: Store,
    gmail: GmailMcp,
    msg: GmailMessage,
) -> TriageResult:
    store.log_event(
        ActivityEvent(
            kind="triage.start",
            email_id=msg.id,
            from_addr=msg.from_addr,
            subject=msg.subject,
        )
    )

    client = AsyncAnthropic(api_key=cfg.anthropic_api_key)
    runner = ToolRunner(cfg, gmail, msg)
    messages: list[MessageParam] = [
        {"role": "user", "content": [{"type": "text", "text": _format_email(msg)}]}
    ]

    usage_acc: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }

    tools_with_cache = list(TOOL_PARAMS)
    if tools_with_cache:
        last = dict(tools_with_cache[-1])
        last["cache_control"] = {"type": "ephemeral"}
        tools_with_cache[-1] = last  # type: ignore[assignment]

    stopped: str | None = None
    iteration = 0

    while iteration < cfg.max_iterations:
        iteration += 1
        resp: Message = await client.messages.create(
            model=cfg.model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=tools_with_cache,
            messages=messages,
        )

        for k in usage_acc:
            usage_acc[k] += getattr(resp.usage, k, 0) or 0

        total_tokens = usage_acc["input_tokens"] + usage_acc["output_tokens"]
        if total_tokens > cfg.max_tokens_per_triage:
            stopped = f"token cap hit ({total_tokens} > {cfg.max_tokens_per_triage})"
            break

        messages.append({"role": "assistant", "content": resp.content})

        tool_uses: list[ToolUseBlock] = [
            b for b in resp.content if isinstance(b, ToolUseBlock)
        ]

        if not tool_uses or resp.stop_reason == "end_turn":
            break

        tool_results: list[ToolResultBlockParam] = []
        for tu in tool_uses:
            outcome = await runner.run(tu.name, tu.input if isinstance(tu.input, dict) else {})
            store.log_event(
                ActivityEvent(
                    kind="triage.tool",
                    email_id=msg.id,
                    tool_name=tu.name,
                    payload={
                        "input": tu.input,
                        "result": outcome.result,
                        "error": outcome.error,
                    },
                )
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": outcome.to_content(),
                    "is_error": not outcome.ok,
                }
            )

        messages.append({"role": "user", "content": tool_results})

        if runner.finished:
            break

    cost = estimate_cost_usd(cfg.model, usage_acc)
    budget_after = store.charge_budget(cost)
    store.log_event(
        ActivityEvent(
            kind="triage.done" if runner.finished else "triage.incomplete",
            email_id=msg.id,
            from_addr=msg.from_addr,
            subject=msg.subject,
            payload={
                "tier": runner.final_tier,
                "summary": runner.final_summary,
                "iterations": iteration,
                "usage": usage_acc,
                "budget_after": {
                    "spent_usd": budget_after.spent_usd,
                    "triage_count": budget_after.triage_count,
                },
                "stopped": stopped,
            },
            cost_usd=cost,
        )
    )
    return TriageResult(
        ok=runner.finished,
        tier=runner.final_tier,
        summary=runner.final_summary,
        iterations=iteration,
        usage=usage_acc,
        cost_usd=cost,
        stopped=stopped,
    )
