from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

# Repos the agent can query for recent merges. Hard allowlist so a
# hallucinated repo name can't trigger arbitrary cross-org fetches.
ALLOWED_RECENT_MERGE_REPOS: frozenset[str] = frozenset(
    {
        "karlmarx/nwb-plan",
        "karlmarx/nwb-yoga",
        "karlmarx/foodr",
        "karlmarx/identity-verification",
        "karlmarx/karl-command-center",
        "karlmarx/karl-infra",
        "karlmarx/blazing-paddles-react",
        "karlmarx/mom-93fyi",
        "karlmarx/93-fyi",
        "karlmarx/me-93fyi",
        "karlmarx/paperclip-sandbox",
    }
)


@dataclass
class CreatedIssue:
    number: int
    url: str


@dataclass
class RecentMerge:
    number: int
    title: str
    author: str
    merged_at: str
    url: str


async def create_issue(
    *,
    token: str,
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> CreatedIssue:
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "authorization": f"Bearer {token}",
                "accept": "application/vnd.github+json",
                "user-agent": "karl-triage",
            },
            json={"title": title, "body": body, "labels": labels or []},
        )
        res.raise_for_status()
        data = res.json()
    return CreatedIssue(number=data["number"], url=data["html_url"])


async def list_recent_merges(
    *,
    token: str,
    repo: str,
    hours: int = 48,
) -> list[RecentMerge]:
    if repo not in ALLOWED_RECENT_MERGE_REPOS:
        raise ValueError(
            f"repo {repo!r} not in recent-merges allowlist"
        )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[RecentMerge] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"https://api.github.com/repos/{repo}/pulls",
            headers={
                "authorization": f"Bearer {token}",
                "accept": "application/vnd.github+json",
                "user-agent": "karl-triage",
            },
            params={
                "state": "closed",
                "base": "main",
                "sort": "updated",
                "direction": "desc",
                "per_page": 20,
            },
        )
        res.raise_for_status()
        for pr in res.json():
            merged_at = pr.get("merged_at")
            if not merged_at:
                continue
            try:
                ts = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts < cutoff:
                continue
            out.append(
                RecentMerge(
                    number=pr["number"],
                    title=pr["title"],
                    author=(pr.get("user") or {}).get("login", "unknown"),
                    merged_at=merged_at,
                    url=pr["html_url"],
                )
            )
    return out
