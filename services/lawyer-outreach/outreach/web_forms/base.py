from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import (
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

from ..models import ClientProfile, Firm

log = logging.getLogger(__name__)


@dataclass
class FormFillResult:
    success: bool
    submitted: bool
    needs_manual: bool
    screenshot_path: str | None
    detail: str


# Heuristic mapping: regex on (name|id|placeholder|aria-label) -> profile attr.
# Order matters — first match wins.
FIELD_HINTS: list[tuple[str, str]] = [
    (r"first[\s_-]*name|fname|given[\s_-]*name", "first_name"),
    (r"last[\s_-]*name|lname|family[\s_-]*name|surname", "last_name"),
    (r"full[\s_-]*name|your[\s_-]*name|name\b", "full_name"),
    (r"email", "email"),
    (r"phone|mobile|cell|tel", "phone"),
    (r"\bcity\b", "city"),
    (r"\bstate\b|province", "state"),
    (r"zip|postal", "zip"),
    (r"age", "age"),
    (r"gender|\bsex\b", "sex"),
    (r"injury|condition|complaint|diagnosis|tell\s*us|describe|comment|message|details|story|case", "case_summary"),
    (r"prescrip|medication|drug|truvada|tdf", "indication_text"),
    (r"date.*injury|injury.*date|when.*occur", "injury_date"),
]


def _field_value(profile: ClientProfile, key: str) -> str | None:
    # Build a flat lookup from ClientProfile + a generated case summary.
    parts = profile.full_name.split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    case_summary = (
        f"I have been taking Truvada for {profile.indication} since "
        f"{profile.truvada_start_year}. {profile.injury_summary} "
        f"DEXA findings: {profile.dexa_findings}."
    )
    if profile.other_relevant:
        case_summary += f" {profile.other_relevant}"

    table = {
        "first_name": first,
        "last_name": last,
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "state": profile.state,
        "zip": "",
        "age": str(profile.age),
        "sex": profile.sex,
        "case_summary": case_summary,
        "indication_text": f"Truvada (tenofovir disoproxil) for {profile.indication}",
        "injury_date": profile.injury_date,
    }
    return table.get(key)


def _label_text(input_el) -> str:
    parts: list[str] = []
    for attr in ("name", "id", "placeholder", "aria-label"):
        try:
            v = input_el.get_attribute(attr)
        except Exception:
            v = None
        if v:
            parts.append(v)
    return " | ".join(parts).lower()


def _match_field(label: str) -> str | None:
    for pattern, key in FIELD_HINTS:
        if re.search(pattern, label, re.IGNORECASE):
            return key
    return None


def _detect_captcha(page: Page) -> bool:
    needles = [
        "recaptcha",
        "g-recaptcha",
        "hcaptcha",
        "h-captcha",
        "cf-turnstile",
        "cloudflare/turnstile",
    ]
    try:
        html = page.content()[:200_000].lower()
    except Exception:
        return False
    return any(n in html for n in needles)


def fill_intake_form(
    firm: Firm,
    profile: ClientProfile,
    screenshots_dir: Path,
    *,
    submit: bool = True,
    headless: bool = True,
    timeout_ms: int = 45_000,
) -> FormFillResult:
    """Generic heuristic Playwright form filler.

    Returns a FormFillResult. If a CAPTCHA is detected we screenshot the page
    in a half-filled state and exit with needs_manual=True — these have to be
    handed off to the human.
    """
    if not firm.web_form_url:
        return FormFillResult(
            success=False, submitted=False, needs_manual=False,
            screenshot_path=None, detail="no web_form_url configured",
        )

    screenshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    shot_path = screenshots_dir / f"{firm.slug}-{stamp}.png"

    with sync_playwright() as pw:  # type: Playwright
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Apple Silicon) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            page.set_default_timeout(timeout_ms)
            try:
                page.goto(firm.web_form_url, wait_until="networkidle")
            except PlaywrightTimeout:
                # Some sites never reach networkidle; domcontentloaded is fine.
                page.goto(firm.web_form_url, wait_until="domcontentloaded")

            page.wait_for_timeout(1500)

            filled = _fill_visible_fields(page, profile)

            # Save a screenshot BEFORE submit so we have evidence either way.
            page.screenshot(path=str(shot_path), full_page=True)

            if _detect_captcha(page) or firm.has_captcha:
                browser.close()
                return FormFillResult(
                    success=False, submitted=False, needs_manual=True,
                    screenshot_path=str(shot_path),
                    detail=f"captcha detected; filled {filled} fields then bailed",
                )

            if not submit:
                browser.close()
                return FormFillResult(
                    success=True, submitted=False, needs_manual=False,
                    screenshot_path=str(shot_path),
                    detail=f"dry-run; filled {filled} fields",
                )

            submitted = _click_submit(page)

            # Wait briefly for navigation / thank-you message.
            page.wait_for_timeout(3000)
            try:
                page.screenshot(path=str(shot_path).replace(".png", "-after.png"), full_page=True)
            except Exception:
                pass

            detail = f"filled {filled} fields; clicked submit={submitted}"
            return FormFillResult(
                success=submitted, submitted=submitted, needs_manual=not submitted,
                screenshot_path=str(shot_path), detail=detail,
            )
        except Exception as e:
            try:
                page.screenshot(path=str(shot_path), full_page=True)
            except Exception:
                pass
            return FormFillResult(
                success=False, submitted=False, needs_manual=True,
                screenshot_path=str(shot_path), detail=f"error: {e!r}",
            )
        finally:
            try:
                browser.close()
            except Exception:
                pass


def _fill_visible_fields(page: Page, profile: ClientProfile) -> int:
    filled = 0
    inputs = page.locator(
        "input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select"
    )
    count = inputs.count()
    for i in range(count):
        el = inputs.nth(i)
        try:
            if not el.is_visible():
                continue
        except Exception:
            continue
        label = _label_text(el)
        if not label:
            continue
        key = _match_field(label)
        if not key:
            continue
        value = _field_value(profile, key)
        if value is None or value == "":
            continue
        try:
            tag = (el.evaluate("e => e.tagName.toLowerCase()") or "").lower()
            input_type = (el.get_attribute("type") or "").lower()
            if tag == "select":
                try:
                    el.select_option(label=value)
                except Exception:
                    el.select_option(value=value)
            elif input_type in {"checkbox", "radio"}:
                continue  # don't blindly tick consent boxes
            else:
                el.fill(value)
            filled += 1
            log.debug("filled %r with %r", label[:60], value[:60])
        except Exception as e:
            log.debug("could not fill %r: %r", label[:60], e)
    return filled


def _click_submit(page: Page) -> bool:
    candidates = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Send')",
        "button:has-text('Get a free')",
        "button:has-text('Free Case')",
        "button:has-text('Contact')",
    ]
    for sel in candidates:
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click()
                return True
        except Exception:
            continue
    return False
