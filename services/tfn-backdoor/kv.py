"""Redis client + KV contract for the Twilio DTMF backdoor (Mac side).

Vercel writes intents over the Upstash REST API (@vercel/kv); this side connects
over the native Redis TLS endpoint so it can BLPOP (block). The rediss:// URL is
read from the macOS Keychain service `nwb-tfn-redis-url` (prompts on every read).
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass

import redis

PENDING = "tfn:intents:pending"
STATUS = "tfn:status:current"
AUDIT = "tfn:audit"


def _redis_url() -> str:
    out = subprocess.run(
        ["security", "find-generic-password", "-a", os.environ["USER"], "-s", "nwb-tfn-redis-url", "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def client() -> "redis.Redis":
    return redis.from_url(_redis_url(), decode_responses=True)


@dataclass
class Intent:
    id: str
    action: str
    tier: str
    callSid: str
    ts: int

    @classmethod
    def from_json(cls, raw: str) -> "Intent":
        d = json.loads(raw)
        return cls(
            id=d["id"],
            action=d["action"],
            tier=d["tier"],
            callSid=d.get("callSid", ""),
            ts=int(d.get("ts", 0)),
        )


def write_result(r: "redis.Redis", intent_id: str, status: str, speech: str) -> None:
    payload = json.dumps({"status": status, "speech": speech, "ts": int(time.time() * 1000)})
    r.set(f"tfn:result:{intent_id}", payload, ex=300)


def publish_status(r: "redis.Redis", status: dict) -> None:
    r.set(STATUS, json.dumps(status), ex=180)


def audit(r: "redis.Redis", line: dict) -> None:
    entry = {**line, "ts": int(time.time() * 1000)}
    r.lpush(AUDIT, json.dumps(entry))
    r.ltrim(AUDIT, 0, 999)
