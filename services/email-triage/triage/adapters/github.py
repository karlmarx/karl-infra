from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class CreatedIssue:
    number: int
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
