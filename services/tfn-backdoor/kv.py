"""Redis client + KV contract for the Twilio DTMF backdoor (Mac side).

Vercel writes intents over the Upstash REST API (@vercel/kv); this side connects
over the native Redis TLS endpoint so it can BLPOP (block). The rediss:// URL is
read from the macOS Keychain service `nwb-tfn-redis-url` (prompts on every read).
"""
from __future__ import annotations

import getpass
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
    """Read the rediss:// URL from Keychain.

    Env override (TFN_REDIS_URL) wins if set. The Keychain entry is pinned with
    `-T /usr/bin/security` so this read never prompts — required under launchd,
    which has no GUI to answer a Keychain dialog. USER may be unset under
    launchd, so resolve the account name via getpass, not os.environ["USER"].
    """
    env = os.environ.get("TFN_REDIS_URL")
    if env:
        return env.strip()
    acct = os.environ.get("USER") or getpass.getuser()
    out = subprocess.run(
        ["security", "find-generic-password", "-a", acct, "-s", "nwb-tfn-redis-url", "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def client() -> "redis.Redis":
    # socket_timeout must exceed the BLPOP block time (5s) or the read times out
    # mid-block; keep TCP alive so Upstash doesn't drop the idle connection.
    return redis.from_url(
        _redis_url(),
        decode_responses=True,
        socket_timeout=30,
        socket_keepalive=True,
        health_check_interval=30,
        retry_on_timeout=True,
    )


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
