from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class CreatedTask:
    id: str
    url: str


async def create_task(
    *,
    token: str,
    content: str,
    description: str | None = None,
    priority: int | None = None,
    due_string: str | None = None,
) -> CreatedTask:
    body: dict = {"content": content}
    if description:
        body["description"] = description
    if priority:
        body["priority"] = priority
    if due_string:
        body["due_string"] = due_string
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            "https://api.todoist.com/api/v1/tasks",
            headers={
                "authorization": f"Bearer {token}",
                "content-type": "application/json",
            },
            json=body,
        )
        res.raise_for_status()
        data = res.json()
    return CreatedTask(id=str(data["id"]), url=data.get("url", ""))
