from __future__ import annotations

import base64
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

log = logging.getLogger(__name__)


@dataclass
class GmailMessage:
    id: str
    thread_id: str
    from_addr: str
    to: str
    subject: str
    snippet: str
    body: str
    date_ms: int


class GmailMcp:
    """Wrapper around the local Gmail MCP server.

    The user's Gmail MCP server may expose tools with various names. This
    wrapper tries a small set of conventional tool names and falls back to
    scanning tools/list. The tool names we accept (in priority order):

        list_unread_messages | search_emails | list_messages
        get_message          | read_email    | get_email
        modify_message_labels | add_label    | apply_label
        create_draft         | draft_reply
    """

    def __init__(self, session: ClientSession) -> None:
        self.session = session
        self._tools: dict[str, Any] = {}

    async def init(self) -> None:
        await self.session.initialize()
        listing = await self.session.list_tools()
        self._tools = {t.name: t for t in listing.tools}
        log.info("gmail mcp tools: %s", list(self._tools.keys()))

    def _pick(self, candidates: list[str]) -> str:
        for c in candidates:
            if c in self._tools:
                return c
        raise RuntimeError(
            f"Gmail MCP server does not expose any of: {candidates}. "
            f"Available: {list(self._tools.keys())}"
        )

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        res = await self.session.call_tool(name, arguments=arguments)
        if res.isError:
            raise RuntimeError(f"{name} failed: {res.content}")
        if res.content and len(res.content) > 0:
            first = res.content[0]
            text = getattr(first, "text", None)
            if text is not None:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return None

    async def list_recent(
        self, sender_allowlist: list[str], max_results: int = 10
    ) -> list[dict[str, str]]:
        tool = self._pick(["search_emails", "list_unread_messages", "list_messages"])
        from_q = " OR ".join(f"from:{s}" for s in sender_allowlist)
        query = f"({from_q}) -label:triaged newer_than:1d"
        out = await self._call(tool, {"query": query, "maxResults": max_results})
        items = out.get("messages") if isinstance(out, dict) else out
        if not items:
            return []
        return [
            {"id": m.get("id") or m.get("message_id"), "thread_id": m.get("threadId") or m.get("thread_id", "")}
            for m in items
            if (m.get("id") or m.get("message_id"))
        ]

    async def get_message(self, message_id: str) -> GmailMessage:
        tool = self._pick(["get_message", "read_email", "get_email"])
        out = await self._call(tool, {"messageId": message_id, "id": message_id})
        if not isinstance(out, dict):
            raise RuntimeError(f"unexpected get_message output: {out!r}")
        headers = _headers(out)
        body = _extract_body(out)
        return GmailMessage(
            id=out.get("id") or message_id,
            thread_id=out.get("threadId") or out.get("thread_id") or "",
            from_addr=headers.get("from", ""),
            to=headers.get("to", ""),
            subject=headers.get("subject", "(no subject)"),
            snippet=out.get("snippet", ""),
            body=body,
            date_ms=int(out.get("internalDate") or 0),
        )

    async def apply_label(self, message_id: str, label_name: str) -> None:
        tool = self._pick(
            ["modify_message_labels", "add_label", "apply_label", "modify_email_labels"]
        )
        await self._call(
            tool,
            {
                "messageId": message_id,
                "id": message_id,
                "addLabelNames": [label_name],
                "addLabels": [label_name],
                "labelNames": [label_name],
            },
        )

    async def create_draft(self, message: GmailMessage, body_text: str) -> str:
        tool = self._pick(["create_draft", "draft_reply", "draft_email"])
        out = await self._call(
            tool,
            {
                "to": message.from_addr,
                "subject": f"Re: {message.subject}",
                "body": body_text,
                "threadId": message.thread_id,
                "inReplyTo": message.id,
            },
        )
        if isinstance(out, dict):
            return out.get("id") or out.get("draftId") or "(unknown)"
        return "(unknown)"


def _headers(msg: dict[str, Any]) -> dict[str, str]:
    payload = msg.get("payload") or {}
    raw = payload.get("headers") or msg.get("headers") or []
    out: dict[str, str] = {}
    for h in raw:
        name = (h.get("name") or "").lower()
        out[name] = h.get("value", "")
    return out


def _extract_body(msg: dict[str, Any]) -> str:
    if msg.get("body") and isinstance(msg["body"], str):
        return msg["body"]
    payload = msg.get("payload") or {}
    return _walk_payload(payload)


def _walk_payload(payload: dict[str, Any]) -> str:
    if payload.get("mimeType") == "text/plain":
        data = (payload.get("body") or {}).get("data")
        if data:
            return _decode_b64url(data)
    for part in payload.get("parts") or []:
        if part.get("mimeType") == "text/plain":
            data = (part.get("body") or {}).get("data")
            if data:
                return _decode_b64url(data)
    for part in payload.get("parts") or []:
        nested = _walk_payload(part)
        if nested:
            return nested
    return ""


def _decode_b64url(s: str) -> str:
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="replace")
    except Exception:
        return ""


@asynccontextmanager
async def connect_gmail_mcp(
    command: str, args: list[str]
) -> AsyncIterator[GmailMcp]:
    params = StdioServerParameters(command=command, args=args, env=None)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            mcp = GmailMcp(session)
            await mcp.init()
            yield mcp
