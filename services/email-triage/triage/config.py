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

    # Gmail access — either IMAP (app password, simpler) or MCP (OAuth).
    # ``connect_gmail`` picks IMAP if app_password is set, else falls back to MCP.
    gmail_mcp_command: str | None
    gmail_mcp_args: list[str]
    gmail_user: str | None
    gmail_app_password: str | None

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

    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD") or None
    gmail_user = os.environ.get("GMAIL_USER") or None
    gmail_mcp_command = os.environ.get("GMAIL_MCP_COMMAND") or None
    gmail_mcp_args = os.environ.get("GMAIL_MCP_ARGS", "").split()

    if gmail_app_password and not gmail_user:
        raise RuntimeError("GMAIL_APP_PASSWORD requires GMAIL_USER")
    if not gmail_app_password and not gmail_mcp_command:
        raise RuntimeError(
            "configure either GMAIL_APP_PASSWORD+GMAIL_USER (IMAP) "
            "or GMAIL_MCP_COMMAND+GMAIL_MCP_ARGS (MCP)"
        )

    return Config(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        model=os.environ.get("TRIAGE_MODEL", "claude-opus-4-7"),
        supabase_url=_require("SUPABASE_URL"),
        supabase_service_role_key=_require("SUPABASE_SERVICE_ROLE_KEY"),
        gmail_mcp_command=gmail_mcp_command,
        gmail_mcp_args=gmail_mcp_args,
        gmail_user=gmail_user,
        gmail_app_password=gmail_app_password,
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
