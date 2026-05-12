from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from anthropic.types import ToolParam

from .adapters import github as gh_adapter
from .adapters import todoist as todoist_adapter
from .adapters import twilio as twilio_adapter
from .config import Config
from .gmail_mcp import GmailMcp, GmailMessage

log = logging.getLogger(__name__)


TOOL_PARAMS: list[ToolParam] = [
    {
        "name": "gmail_apply_label",
        "description": (
            "Add a Gmail label to the email being triaged. Use one of: "
            "triaged/urgent, triaged/normal, triaged/low, triaged/bug, triaged/spam."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Label name to apply."},
            },
            "required": ["label"],
        },
    },
    {
        "name": "gmail_draft_reply",
        "description": (
            "Create a DRAFT reply to the email being triaged. Does not send. "
            "Use when a personal reply is warranted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "description": "Plain-text reply body."},
            },
            "required": ["body"],
        },
    },
    {
        "name": "todoist_create_task",
        "description": "Create a Todoist task for follow-up by Karl.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Short title."},
                "description": {
                    "type": "string",
                    "description": "Longer body (include email snippet + sender).",
                },
                "priority": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "description": "1=lowest, 4=highest.",
                },
                "due_string": {
                    "type": "string",
                    "description": "Natural-language due like 'tomorrow 9am'.",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "github_create_issue",
        "description": (
            "Create a GitHub issue. Use ONLY when the email is a bug report, "
            "feature request, or other code-related action item."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "owner/repo. Omit to use the default repo.",
                },
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "twilio_send_urgent_sms",
        "description": (
            "Send an SMS to Karl's phone. Use ONLY for truly urgent emails "
            "(time-sensitive, blocking, or financial). The SMS body must be "
            "short (<= 160 chars) and include the subject + sender."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "description": "<= 160 chars."},
            },
            "required": ["body"],
        },
    },
    {
        "name": "finish_triage",
        "description": (
            "Call this exactly ONCE when triage is complete. Provide a "
            "1-sentence summary and the chosen tier."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "tier": {
                    "type": "string",
                    "enum": ["urgent", "normal", "low", "bug", "spam"],
                },
            },
            "required": ["summary", "tier"],
        },
    },
]


@dataclass
class ToolOutcome:
    ok: bool
    result: Any = None
    error: str | None = None

    def to_content(self) -> str:
        import json

        return json.dumps(
            {"ok": self.ok, "result": self.result, "error": self.error},
            default=str,
        )


class ToolRunner:
    def __init__(self, cfg: Config, gmail: GmailMcp, message: GmailMessage) -> None:
        self.cfg = cfg
        self.gmail = gmail
        self.message = message
        self.finished = False
        self.final_tier: str | None = None
        self.final_summary: str | None = None

    async def run(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        try:
            if name == "gmail_apply_label":
                await self.gmail.apply_label(self.message.id, args["label"])
                return ToolOutcome(True, {"labeled": args["label"]})

            if name == "gmail_draft_reply":
                draft_id = await self.gmail.create_draft(self.message, args["body"])
                return ToolOutcome(True, {"draft_id": draft_id})

            if name == "todoist_create_task":
                task = await todoist_adapter.create_task(
                    token=self.cfg.todoist_token,
                    content=args["content"],
                    description=args.get("description"),
                    priority=args.get("priority"),
                    due_string=args.get("due_string"),
                )
                return ToolOutcome(True, {"id": task.id, "url": task.url})

            if name == "github_create_issue":
                repo = args.get("repo") or self.cfg.default_gh_repo
                issue = await gh_adapter.create_issue(
                    token=self.cfg.github_token,
                    repo=repo,
                    title=args["title"],
                    body=args["body"],
                    labels=args.get("labels"),
                )
                return ToolOutcome(
                    True, {"number": issue.number, "url": issue.url, "repo": repo}
                )

            if name == "twilio_send_urgent_sms":
                if not self.cfg.twilio_enabled:
                    return ToolOutcome(False, error="twilio not configured")
                sms = await twilio_adapter.send_sms(
                    account_sid=self.cfg.twilio_account_sid,  # type: ignore[arg-type]
                    auth_token=self.cfg.twilio_auth_token,  # type: ignore[arg-type]
                    from_number=self.cfg.twilio_from,  # type: ignore[arg-type]
                    to_number=self.cfg.twilio_to,  # type: ignore[arg-type]
                    body=args["body"],
                )
                return ToolOutcome(True, {"sid": sms.sid, "status": sms.status})

            if name == "finish_triage":
                self.finished = True
                self.final_tier = args.get("tier")
                self.final_summary = args.get("summary")
                return ToolOutcome(
                    True, {"summary": self.final_summary, "tier": self.final_tier}
                )

            return ToolOutcome(False, error=f"unknown tool: {name}")
        except Exception as e:
            log.exception("tool %s failed", name)
            return ToolOutcome(False, error=str(e))
