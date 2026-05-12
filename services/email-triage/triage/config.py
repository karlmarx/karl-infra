from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    anthropic_api_key: str
    model: str

    supabase_url: str
    supabase_service_role_key: str

    gmail_mcp_command: str
    gmail_mcp_args: list[str]

    github_token: str
    default_gh_repo: str

    todoist_token: str

    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from: str | None
    twilio_to: str | None

    nwb_postgres_url: str | None

    sender_allowlist: list[str] = field(default_factory=list)
    daily_budget_usd: float = 1.0
    max_triages_per_day: int = 50
    max_tokens_per_triage: int = 12000
    max_iterations: int = 6

    @property
    def twilio_enabled(self) -> bool:
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from
            and self.twilio_to
        )


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"missing required env var: {name}")
    return val


def load_config(env_file: Path | None = None) -> Config:
    if env_file and env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()

    allow = [
        s.strip().lower()
        for s in os.environ.get("SENDER_ALLOWLIST", "").split(",")
        if s.strip()
    ]
    if not allow:
        raise RuntimeError("SENDER_ALLOWLIST must contain at least one address")

    return Config(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        model=os.environ.get("TRIAGE_MODEL", "claude-opus-4-7"),
        supabase_url=_require("SUPABASE_URL"),
        supabase_service_role_key=_require("SUPABASE_SERVICE_ROLE_KEY"),
        gmail_mcp_command=_require("GMAIL_MCP_COMMAND"),
        gmail_mcp_args=os.environ.get("GMAIL_MCP_ARGS", "").split(),
        github_token=_require("GITHUB_TOKEN"),
        default_gh_repo=os.environ.get("DEFAULT_GH_REPO", "karlmarx/karl-command-center"),
        todoist_token=_require("TODOIST_TOKEN"),
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID") or None,
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN") or None,
        twilio_from=os.environ.get("TWILIO_FROM") or None,
        twilio_to=os.environ.get("TWILIO_TO") or None,
        nwb_postgres_url=os.environ.get("NWB_POSTGRES_URL") or None,
        sender_allowlist=allow,
        daily_budget_usd=float(os.environ.get("DAILY_BUDGET_USD", "1.0")),
        max_triages_per_day=int(os.environ.get("MAX_TRIAGES_PER_DAY", "50")),
        max_tokens_per_triage=int(os.environ.get("MAX_TOKENS_PER_TRIAGE", "12000")),
        max_iterations=int(os.environ.get("MAX_ITERATIONS", "6")),
    )
