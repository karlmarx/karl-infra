from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FirmStatus(str, Enum):
    NOT_CONTACTED = "not_contacted"
    EMAIL_SENT = "email_sent"
    EMAIL_DRAFTED = "email_drafted"
    FORM_SUBMITTED = "form_submitted"
    FORM_NEEDS_MANUAL = "form_needs_manual"
    REPLY_RECEIVED = "reply_received"
    DECLINED = "declined"
    ACCEPTED = "accepted"
    SKIPPED = "skipped"
    ERROR = "error"


class Channel(str, Enum):
    EMAIL = "email"
    WEB_FORM = "web_form"


@dataclass
class Firm:
    slug: str
    name: str
    intake_email: str | None = None
    web_form_url: str | None = None
    phone: str | None = None
    location: str | None = None
    notes: str | None = None
    web_form_adapter: str = "generic"
    accepts_prep: str = "unclear"  # "yes" | "no" | "unclear"
    still_accepting: str = "unclear"
    has_captcha: bool = False
    skip: bool = False
    skip_reason: str | None = None
    source_url: str | None = None
    # Channel preference: try web form first, fall back to email, or pick one.
    channels: list[str] = field(default_factory=lambda: ["email"])
    # Tone/personalization hints used by the composer
    personalization_hints: str | None = None


@dataclass
class ClientProfile:
    """User-provided injury details. Lives in client.yaml (gitignored)."""

    full_name: str
    email: str
    phone: str
    city: str
    state: str
    age: int
    sex: str
    # Indication for Truvada use
    indication: str  # "PrEP" | "HIV treatment"
    truvada_start_year: int | str  # int year or "{TRUVADA_START_YEAR}" placeholder
    truvada_still_taking: bool
    # Injury
    injury_summary: str
    injury_date: str  # ISO date or placeholder
    diagnosing_provider: str | None
    dexa_findings: str
    treating_specialty: str | None
    other_relevant: str | None = None
