from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from .compose import Composed, compose_email
from .config import Config
from .email_send import send_email
from .firms import eligible_firms, load_client, load_firms
from .models import ClientProfile, Firm
from .reply_scan import scan_replies
from .state import Attempt, State
from .web_forms import fill_intake_form

log = logging.getLogger(__name__)


def _kill_switch_active(cfg: Config) -> bool:
    if cfg.kill_switch_file.exists():
        log.warning("kill switch active: %s", cfg.kill_switch_file)
        return True
    return False


def _verify_placeholders_filled(profile: ClientProfile) -> list[str]:
    """Return list of placeholder fields still unfilled."""
    issues: list[str] = []
    if "[" in str(profile.truvada_start_year) or "PLACEHOLDER" in str(profile.truvada_start_year).upper():
        issues.append("truvada_start_year")
    if "[" in profile.injury_date or "PLACEHOLDER" in profile.injury_date.upper():
        issues.append("injury_date")
    if "[" in profile.injury_summary:
        issues.append("injury_summary")
    return issues


def run_outreach(cfg: Config) -> int:
    """One outreach cycle. Returns count of new sends/submissions in this run."""
    if _kill_switch_active(cfg):
        return 0

    profile = load_client(cfg.client_yaml)
    firms = load_firms(cfg.firms_yaml)
    candidates = eligible_firms(firms)

    state = State(cfg.state_db)
    sends_today = state.sends_today()
    if sends_today >= cfg.max_firms_per_day:
        log.info("daily cap reached (%d/%d) — exiting", sends_today, cfg.max_firms_per_day)
        return 0

    last_send = state.last_send_at()
    if last_send:
        elapsed = (datetime.now(timezone.utc) - last_send).total_seconds()
        if elapsed < cfg.min_seconds_between_sends:
            wait = int(cfg.min_seconds_between_sends - elapsed)
            log.info("throttled — last send %.0fs ago, wait %ds", elapsed, wait)
            return 0

    pending_slugs = state.firms_not_yet_contacted([f.slug for f in candidates])
    if not pending_slugs:
        log.info("no firms left to contact")
        return 0

    # Process one firm per invocation. launchd re-invokes us on schedule.
    slug = pending_slugs[0]
    firm = next(f for f in candidates if f.slug == slug)

    # Placeholder gate: refuse to send mass outreach if the profile still
    # has unfilled [PLACEHOLDER] fields and we're in auto mode.
    missing = _verify_placeholders_filled(profile)
    if missing and cfg.auto_send:
        msg = f"client profile has unfilled placeholders: {missing}"
        log.error(msg)
        state.set_firm_status(slug, "error", last_error=msg)
        return 0

    anth = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    composed = compose_email(anth, cfg.model, firm, profile)

    sent_anything = 0

    # Channel selection
    channels = firm.channels or ["email"]
    if not cfg.enable_web_forms:
        channels = [c for c in channels if c != "web_form"]

    for channel in channels:
        if channel == "web_form":
            if not firm.web_form_url:
                continue
            result = fill_intake_form(
                firm,
                profile,
                cfg.screenshots_dir,
                submit=cfg.auto_send,
                headless=True,
            )
            attempt = Attempt(
                firm_slug=firm.slug,
                channel="web_form",
                sent_at=datetime.now(timezone.utc).isoformat(),
                status="submitted" if result.submitted else ("manual" if result.needs_manual else "drafted"),
                subject=None,
                message_excerpt=result.detail[:300],
                form_screenshot_path=result.screenshot_path,
                detail={"submitted": result.submitted, "needs_manual": result.needs_manual},
            )
            state.record_attempt(attempt)
            if result.submitted:
                state.set_firm_status(slug, "form_submitted", channel="web_form")
                sent_anything += 1
            elif result.needs_manual:
                state.set_firm_status(slug, "form_needs_manual", channel="web_form",
                                      notes=result.detail)
            else:
                state.set_firm_status(slug, "error", channel="web_form", last_error=result.detail)
            # On submitted form, don't also send the email — avoid double-contact.
            if result.submitted:
                state.charge_send(dollars=_estimate_cost(composed))
                _jitter()
                return sent_anything

        elif channel == "email":
            if not firm.intake_email:
                continue
            if cfg.auto_send:
                try:
                    message_id = send_email(
                        gmail_user=cfg.gmail_user,
                        gmail_app_password=cfg.gmail_app_password,
                        from_name=cfg.from_name,
                        reply_to=cfg.reply_to,
                        to_addr=firm.intake_email,
                        subject=composed.subject,
                        body=composed.body,
                    )
                    state.record_attempt(Attempt(
                        firm_slug=firm.slug,
                        channel="email",
                        sent_at=datetime.now(timezone.utc).isoformat(),
                        status="sent",
                        subject=composed.subject,
                        message_excerpt=composed.body[:300],
                        message_id=message_id,
                    ))
                    state.set_firm_status(slug, "email_sent", channel="email")
                    state.charge_send(dollars=_estimate_cost(composed))
                    sent_anything += 1
                except Exception as e:
                    log.exception("send failed for %s", firm.slug)
                    state.set_firm_status(slug, "error", channel="email", last_error=str(e))
            else:
                _write_draft_to_disk(cfg.log_dir, firm, composed)
                state.record_attempt(Attempt(
                    firm_slug=firm.slug,
                    channel="email",
                    sent_at=datetime.now(timezone.utc).isoformat(),
                    status="drafted",
                    subject=composed.subject,
                    message_excerpt=composed.body[:300],
                ))
                state.set_firm_status(slug, "email_drafted", channel="email")
                sent_anything += 1

    _jitter()
    return sent_anything


def _jitter() -> None:
    time.sleep(random.uniform(1.0, 4.0))


def _estimate_cost(composed: Composed) -> float:
    # Rough estimate based on Opus pricing — keep cents-accurate enough to
    # cap daily spend, not for accounting. ~3k input + 800 output tokens.
    return 0.05


def _write_draft_to_disk(log_dir: Path, firm: Firm, composed: Composed) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"draft-{firm.slug}-{stamp}.eml"
    body = (
        f"To: {firm.intake_email}\n"
        f"Subject: {composed.subject}\n"
        f"\n"
        f"{composed.body}\n"
    )
    path.write_text(body, encoding="utf-8")
    log.info("wrote draft: %s", path)
    return path


def run_reply_scan(cfg: Config) -> int:
    """Scan Gmail for replies and update state. Returns count of new replies."""
    if not cfg.enable_reply_scan:
        return 0
    firms = load_firms(cfg.firms_yaml)
    state = State(cfg.state_db)
    new = scan_replies(
        gmail_user=cfg.gmail_user,
        gmail_app_password=cfg.gmail_app_password,
        firms=firms,
        state=state,
    )
    log.info("reply scan complete: %d new replies", len(new))
    return len(new)
