from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2].parent
SERVICE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Config:
    """Runtime configuration for lawyer-outreach.

    All paths default under ~/karl-infra-state/lawyer-outreach/ so the service
    keeps its data outside the git repo. Override individual paths with env
    vars when running in CI or tests.
    """

    anthropic_api_key: str
    model: str

    gmail_user: str
    gmail_app_password: str
    from_name: str
    reply_to: str

    client_yaml: Path
    firms_yaml: Path
    state_db: Path
    screenshots_dir: Path
    log_dir: Path

    # Throttling
    max_firms_per_day: int
    min_seconds_between_sends: int
    daily_budget_usd: float

    # Behavior
    send_mode: str  # "draft" | "auto"
    enable_web_forms: bool
    enable_reply_scan: bool
    kill_switch_file: Path

    # Optional integrations
    todoist_token: str | None

    @property
    def auto_send(self) -> bool:
        return self.send_mode.lower() == "auto"


def _env(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"missing required env var: {name}")
    return val


def load_config(env_file: Path | None = None) -> Config:
    if env_file and env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv(SERVICE_ROOT / ".env")

    state_root = Path(
        os.environ.get("OUTREACH_STATE_ROOT", str(Path.home() / "karl-infra-state" / "lawyer-outreach"))
    )
    state_root.mkdir(parents=True, exist_ok=True)

    return Config(
        anthropic_api_key=_env("ANTHROPIC_API_KEY", required=True),  # type: ignore[arg-type]
        model=os.environ.get("OUTREACH_MODEL", "claude-opus-4-7"),
        gmail_user=_env("GMAIL_USER", required=True),  # type: ignore[arg-type]
        gmail_app_password=_env("GMAIL_APP_PASSWORD", required=True),  # type: ignore[arg-type]
        from_name=os.environ.get("FROM_NAME", "Karl Marx"),
        reply_to=os.environ.get("REPLY_TO", os.environ.get("GMAIL_USER", "")),
        client_yaml=Path(os.environ.get("CLIENT_YAML", str(SERVICE_ROOT / "client.yaml"))),
        firms_yaml=Path(os.environ.get("FIRMS_YAML", str(SERVICE_ROOT / "outreach" / "firms.yaml"))),
        state_db=Path(os.environ.get("STATE_DB", str(state_root / "outreach.db"))),
        screenshots_dir=Path(os.environ.get("SCREENSHOTS_DIR", str(state_root / "screenshots"))),
        log_dir=Path(os.environ.get("LOG_DIR", str(state_root / "logs"))),
        max_firms_per_day=int(os.environ.get("MAX_FIRMS_PER_DAY", "3")),
        min_seconds_between_sends=int(os.environ.get("MIN_SECONDS_BETWEEN_SENDS", "900")),
        daily_budget_usd=float(os.environ.get("DAILY_BUDGET_USD", "1.0")),
        send_mode=os.environ.get("SEND_MODE", "draft"),
        enable_web_forms=os.environ.get("ENABLE_WEB_FORMS", "true").lower() == "true",
        enable_reply_scan=os.environ.get("ENABLE_REPLY_SCAN", "true").lower() == "true",
        kill_switch_file=Path(
            os.environ.get("KILL_SWITCH_FILE", str(state_root / "disable"))
        ),
        todoist_token=os.environ.get("TODOIST_TOKEN") or None,
    )
