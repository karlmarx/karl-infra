#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""mom-93fyi-tollfree-autofixer.

Polls the Twilio toll-free verification status. On TWILIO_REJECTED, looks
up the next un-tried fix strategy in `mom-93fyi-tollfree-strategies.json`
for the rejection reason code, applies it via PATCH (POST), and persists
state so each strategy is only tried once.

Cooldown: at least 2h between attempts (lets Twilio actually re-review).
Hard cap: ``MAX_TOTAL_ATTEMPTS`` (default 8) before notifying for manual
review. macOS notification on every status transition AND on every
strategy fire.

Run manually:
    ./mom-93fyi-tollfree-autofixer.py
    ./mom-93fyi-tollfree-autofixer.py --dry-run
    ./mom-93fyi-tollfree-autofixer.py --force          # bypass cooldown
    ./mom-93fyi-tollfree-autofixer.py --status         # print state, no API call to Twilio
    ./mom-93fyi-tollfree-autofixer.py --reset          # wipe attempt state (use after editing strategies)

Run on schedule:
    Install com.karlmarx.mom-93fyi-tollfree-autofixer.plist
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# --------------------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent
STRATEGY_FILE = HERE / "mom-93fyi-tollfree-strategies.json"
STATE_DIR = Path.home() / ".local" / "state" / "mom-93fyi-tollfree"
LOG_DIR = Path.home() / ".local" / "share" / "mom-93fyi-tollfree"
STATE_FILE = STATE_DIR / "autofix-state.json"
LOG_FILE = LOG_DIR / "autofixer.log"
ENV_FILE = Path.home() / "mom-93fyi" / ".env.production.local"

# --------------------------------------------------------------------------- tunables
MAX_TOTAL_ATTEMPTS = 8
COOLDOWN_HOURS = 2

# --------------------------------------------------------------------------- helpers
def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip("'\"")
    return env


def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "attempts_used": [],
        "code_attempts": {},
        "fallbacks_used": [],
        "last_attempt_at": None,
        "last_status": None,
    }


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def notify_mac(title: str, message: str) -> None:
    # Pass message/title as positional argv so we don't have to escape them
    # into the -e string. This sidesteps Unicode + quote-escaping issues
    # (e.g. → arrows, smart quotes) that broke the inline form.
    script = (
        "on run argv\n"
        "    display notification (item 1 of argv) with title (item 2 of argv)\n"
        "end run"
    )
    try:
        subprocess.run(
            ["osascript", "-e", script, message, title],
            check=False,
            timeout=5,
            capture_output=True,
        )
    except Exception as exc:
        logging.warning("notify failed: %s", exc)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- twilio
def fetch_status(sid: str, key_sid: str, key_secret: str) -> dict:
    url = f"https://messaging.twilio.com/v1/Tollfree/Verifications/{sid}"
    r = requests.get(url, auth=(key_sid, key_secret), timeout=30)
    r.raise_for_status()
    return r.json()


def url_reachable(url: str) -> bool:
    if not url:
        return False
    try:
        r = requests.head(url, allow_redirects=True, timeout=15)
        if r.status_code == 200:
            return True
        r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=15)
        return r.status_code in (200, 206)
    except requests.RequestException:
        return False


def fire_patch(
    sid: str, patch: dict, key_sid: str, key_secret: str
) -> tuple[bool, str]:
    url = f"https://messaging.twilio.com/v1/Tollfree/Verifications/{sid}"
    # Twilio expects list values as repeated form fields; requests handles
    # that automatically when the value is a list/tuple.
    try:
        r = requests.post(url, data=patch, auth=(key_sid, key_secret), timeout=60)
    except requests.RequestException as exc:
        return False, f"request failed: {exc}"
    body = r.text[:600]
    if 200 <= r.status_code < 300:
        return True, body
    return False, f"HTTP {r.status_code}: {body}"


# --------------------------------------------------------------------------- strategy selection
def pick_next_strategy(
    rejection_reasons: list[dict], strategies: dict, fallbacks: list[dict], state: dict
) -> tuple[str, dict] | None:
    """Return (code, strategy_dict) for the next un-tried strategy.

    Skip any strategy flagged ``manual_only: true`` — those signal an
    escalation, not an auto-fix.
    """
    # Try per-code strategies first.
    for r in rejection_reasons:
        code = str(r.get("code"))
        tried = state.get("code_attempts", {}).get(code, [])
        for s in strategies.get(code, []):
            if s.get("manual_only"):
                continue
            if s["name"] not in tried:
                return (code, s)

    # No per-code strategy left — try fallbacks.
    used = state.get("fallbacks_used", [])
    for s in fallbacks:
        if s["name"] not in used:
            return ("*", s)

    return None


# --------------------------------------------------------------------------- status command
def print_status(strategies_doc: dict, state: dict, current: dict | None) -> None:
    sid = strategies_doc["verification_sid"]
    print(f"verification_sid: {sid}")
    if current:
        print(f"twilio_status:    {current.get('status')}")
        rrs = current.get("rejection_reasons") or []
        for r in rrs:
            print(f"  rejection: code={r.get('code')!s:6} {r.get('reason')}")
    attempts = state.get("attempts_used", [])
    print(f"attempts_used:    {len(attempts)}/{MAX_TOTAL_ATTEMPTS}")
    last = state.get("last_attempt_at")
    print(f"last_attempt_at:  {last or '(none)'}")
    if last:
        next_at = datetime.fromisoformat(last) + timedelta(hours=COOLDOWN_HOURS)
        now = datetime.now(timezone.utc)
        if now < next_at:
            print(f"next_eligible_at: {next_at.isoformat()} (cooldown active)")
        else:
            print("next_eligible_at: now")
    print()
    print("strategy history:")
    for code, tried in (state.get("code_attempts") or {}).items():
        avail = strategies_doc.get("rejection_strategies", {}).get(code, [])
        avail_names = [s["name"] for s in avail if not s.get("manual_only")]
        remaining = [n for n in avail_names if n not in tried]
        print(f"  code {code}: tried {len(tried)}/{len(avail_names)}")
        for n in tried:
            print(f"    ✓ {n}")
        for n in remaining:
            print(f"    ◯ {n}")
    used_fb = state.get("fallbacks_used", [])
    fbs = strategies_doc.get("fallback_strategies", [])
    if fbs:
        print(f"  fallbacks: tried {len(used_fb)}/{len(fbs)}")


# --------------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Don't POST; log only.")
    parser.add_argument("--force", action="store_true", help="Bypass cooldown.")
    parser.add_argument(
        "--status", action="store_true", help="Print state and exit (no Twilio write)."
    )
    parser.add_argument(
        "--reset", action="store_true", help="Wipe attempt history. Use after editing strategies."
    )
    args = parser.parse_args()

    setup_logging()
    logging.info("=" * 60)
    logging.info("autofixer start dry_run=%s force=%s", args.dry_run, args.force)

    if not STRATEGY_FILE.is_file():
        logging.error("strategy file missing: %s", STRATEGY_FILE)
        notify_mac("Toll-free autofixer", "strategy file missing")
        return 2
    strategies_doc = json.loads(STRATEGY_FILE.read_text())
    sid = strategies_doc["verification_sid"]
    strategies = strategies_doc.get("rejection_strategies", {})
    fallbacks = strategies_doc.get("fallback_strategies", [])
    base_patch = strategies_doc.get("base_patch", {})

    state = load_state()

    if args.reset:
        state = {
            "attempts_used": [],
            "code_attempts": {},
            "fallbacks_used": [],
            "last_attempt_at": None,
            "last_status": state.get("last_status"),
        }
        save_state(state)
        print("state reset.")
        return 0

    env = load_env(ENV_FILE)
    key_sid = env.get("TWILIO_API_KEY_SID") or os.environ.get("TWILIO_API_KEY_SID")
    key_secret = env.get("TWILIO_API_KEY_SECRET") or os.environ.get(
        "TWILIO_API_KEY_SECRET"
    )
    if not key_sid or not key_secret:
        logging.error("missing TWILIO_API_KEY_SID/SECRET")
        return 2

    try:
        current = fetch_status(sid, key_sid, key_secret)
    except requests.HTTPError as exc:
        logging.error("fetch failed: %s", exc)
        notify_mac("Toll-free autofixer", f"API fetch failed: {exc}")
        return 1

    if args.status:
        print_status(strategies_doc, state, current)
        return 0

    status = current.get("status")
    rejection_reasons = current.get("rejection_reasons") or []
    logging.info("status=%s reasons=%s", status, rejection_reasons)

    # Status-change notifications.
    last_status = state.get("last_status")
    if status != last_status:
        notify_mac(
            "Toll-free status change",
            f"{last_status or 'unknown'} → {status}",
        )
        state["last_status"] = status
        save_state(state)

    if status == "TWILIO_APPROVED":
        logging.info("APPROVED — done")
        if not state.get("notified_approved"):
            notify_mac("Toll-free APPROVED 🎉", f"+18886016132 ready to send SMS")
            state["notified_approved"] = True
            save_state(state)
        return 0

    if status != "TWILIO_REJECTED":
        logging.info("status=%s — nothing to fix", status)
        return 0

    # Hard cap.
    if len(state.get("attempts_used", [])) >= MAX_TOTAL_ATTEMPTS:
        logging.warning(
            "hit MAX_TOTAL_ATTEMPTS (%d) — manual review", MAX_TOTAL_ATTEMPTS
        )
        if not state.get("notified_max_attempts"):
            notify_mac(
                "Toll-free autofixer",
                f"{MAX_TOTAL_ATTEMPTS} attempts exhausted — needs manual review",
            )
            state["notified_max_attempts"] = True
            save_state(state)
        return 0

    # Cooldown.
    if not args.force and state.get("last_attempt_at"):
        last_dt = datetime.fromisoformat(state["last_attempt_at"])
        next_ok = last_dt + timedelta(hours=COOLDOWN_HOURS)
        now = datetime.now(timezone.utc)
        if now < next_ok:
            wait_min = int((next_ok - now).total_seconds() / 60)
            logging.info("cooldown — next attempt eligible in %d min", wait_min)
            return 0

    chosen = pick_next_strategy(rejection_reasons, strategies, fallbacks, state)
    if chosen is None:
        logging.warning("no strategies left for current rejection reasons")
        # Check if any rejection has manual_only flag — surface that specifically.
        manual_reason = None
        for r in rejection_reasons:
            code = str(r.get("code"))
            for s in strategies.get(code, []):
                if s.get("manual_only"):
                    manual_reason = (code, s)
                    break
            if manual_reason:
                break
        if manual_reason and not state.get("notified_manual"):
            code, s = manual_reason
            notify_mac(
                "Toll-free autofixer — manual",
                f"code {code}: {s.get('rationale', s.get('name'))}",
            )
            state["notified_manual"] = True
            save_state(state)
        elif not state.get("notified_no_strategies"):
            notify_mac(
                "Toll-free autofixer",
                "all strategies exhausted for current rejection reasons",
            )
            state["notified_no_strategies"] = True
            save_state(state)
        return 0

    code, strategy = chosen
    logging.info("strategy: code=%s name=%s", code, strategy["name"])

    # Build the patch: base + strategy override.
    patch: dict = {}
    patch.update(base_patch)
    patch.update(strategy.get("patch") or {})

    # Sanity-check the opt-in URL is reachable before firing — avoid burning
    # a strategy on a 404'd asset.
    opt_in = patch.get("OptInImageUrls")
    if opt_in and not url_reachable(opt_in):
        logging.error("OptInImageUrls not reachable (%s) — bailing this cycle", opt_in)
        notify_mac("Toll-free autofixer", f"opt-in URL not reachable: {opt_in}")
        return 1

    # Twilio accepts UseCaseCategories as a comma-separated string OR repeated
    # field. Form-encode the list as repeated field by passing a list.
    if isinstance(patch.get("UseCaseCategories"), list) and len(patch["UseCaseCategories"]) == 1:
        # Pass as scalar — Twilio sometimes rejects single-element list encoding.
        patch["UseCaseCategories"] = patch["UseCaseCategories"][0]

    if args.dry_run:
        logging.info("dry-run patch: %s", json.dumps(patch)[:500])
        return 0

    ok, body = fire_patch(sid, patch, key_sid, key_secret)
    record = {
        "ts": now_iso(),
        "code": code,
        "strategy": strategy["name"],
        "ok": ok,
        "response_preview": body[:200],
    }
    state.setdefault("attempts_used", []).append(record)
    state.setdefault("code_attempts", {}).setdefault(code, []).append(strategy["name"])
    if code == "*":
        state.setdefault("fallbacks_used", []).append(strategy["name"])
    state["last_attempt_at"] = now_iso()
    save_state(state)

    if ok:
        logging.info("fired ok: %s", body[:200])
        notify_mac("Toll-free autofix fired", f"code {code}: {strategy['name']}")
    else:
        logging.error("fire failed: %s", body)
        notify_mac("Toll-free autofix FAILED", body[:160])

    logging.info("autofixer end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
