from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class SentSms:
    sid: str
    status: str


async def send_sms(
    *,
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    body: str,
) -> SentSms:
    async with httpx.AsyncClient(timeout=15.0, auth=(account_sid, auth_token)) as client:
        res = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={"From": from_number, "To": to_number, "Body": body[:1500]},
        )
        res.raise_for_status()
        data = res.json()
    return SentSms(sid=data["sid"], status=data["status"])
