#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""mom-93fyi-tollfree-monitor.

Polls Twilio's toll-free verification status for HH26844a254ed93af0c8732fc48591a535.
On status transitions, sends a macOS notification. On TWILIO_REJECTED, fires the
v2 patch from mom-93fyi-tollfree-v2-patch.json (capped at _max_auto_resubmits
attempts), but only if OptInImageUrls returns 200 — otherwise bails so we don't
resubmit with a broken consent URL.

Run manually: ./mom-93fyi-tollfree-monitor.py
Run on schedule: see com.karlmarx.mom-93fyi-tollfree-monitor.plist
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# --------------------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent
PATCH_FILE = HERE / "mom-93fyi-tollfree-v2-patch.json"
STATE_DIR = Path.home() / ".local" / "state" / "mom-93fyi-tollfree"
LOG_DIR = Path.home() / ".local" / "share" / "mom-93fyi-tollfree"
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = LOG_DIR / "monitor.log"

ENV_FILE = Path.home() / "mom-93fyi" / ".env.production.local"

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
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def notify_mac(title: str, message: str) -> None:
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f"display notification {json.dumps(message)} with title {json.dumps(title)}",
            ],
            check=False,
            timeout=5,
        )
    except Exception as exc:
        logging.warning("notify failed: %s", exc)


# --------------------------------------------------------------------------- core
def fetch_status(sid: str, key_sid: str, key_secret: str) -> dict:
    url = f"https://messaging.twilio.com/v1/Tollfree/Verifications/{sid}"
    r = requests.get(url, auth=(key_sid, key_secret), timeout=30)
    r.raise_for_status()
    return r.json()


def opt_in_url_reachable(url: str) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=15)
        if r.status_code == 200:
            return True
        # some servers don't allow HEAD — try GET range
        r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=15)
        return r.status_code in (200, 206)
    except requests.RequestException:
        return False


def fire_patch(sid: str, patch: dict, key_sid: str, key_secret: str) -> tuple[bool, str]:
    url = f"https://messaging.twilio.com/v1/Tollfree/Verifications/{sid}"
    try:
        r = requests.post(
            url,
            data=patch,
            auth=(key_sid, key_secret),
            timeout=60,
        )
    except requests.RequestException as exc:
        return False, f"request failed: {exc}"
    body = r.text[:600]
    # Twilio toll-free verification POSTs return 202 Accepted for async resubmits.
    if 200 <= r.status_code < 300:
        return True, body
    return False, f"HTTP {r.status_code}: {body}"


# --------------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't POST patches; just log.")
    parser.add_argument("--force", action="store_true", help="Fire patch even if state says we already did. For manual override.")
    args = parser.parse_args()

    setup_logging()
    logging.info("=" * 60)
    logging.info("monitor start (dry_run=%s, force=%s)", args.dry_run, args.force)

    env = load_env(ENV_FILE)
    key_sid = env.get("TWILIO_API_KEY_SID") or os.environ.get("TWILIO_API_KEY_SID")
    key_secret = env.get("TWILIO_API_KEY_SECRET") or os.environ.get("TWILIO_API_KEY_SECRET")
    if not key_sid or not key_secret:
        logging.error("missing TWILIO_API_KEY_SID/SECRET in %s and env", ENV_FILE)
        notify_mac("TF monitor: missing Twilio creds", str(ENV_FILE))
        return 2

    if not PATCH_FILE.is_file():
        logging.error("patch file missing: %s", PATCH_FILE)
        notify_mac("TF monitor: patch file missing", str(PATCH_FILE))
        return 2
    patch_doc = json.loads(PATCH_FILE.read_text())
    sid = patch_doc["_target"]["verification_sid"]
    max_resubmits = int(patch_doc.get("_max_auto_resubmits", 1))
    patch = patch_doc["patch"]

    state = load_state()
    last_status = state.get("last_status")
    attempts = int(state.get("auto_resubmit_attempts", 0))

    try:
        current = fetch_status(sid, key_sid, key_secret)
    except requests.HTTPError as exc:
        logging.error("fetch failed: %s", exc)
        notify_mac("TF monitor: API fetch failed", str(exc))
        return 1

    status = current.get("status")
    rejection_reasons = current.get("rejection_reasons")
    rejection_reason = current.get("rejection_reason")
    logging.info("status=%s rejection_reason=%s rejection_reasons=%s", status, rejection_reason, rejection_reasons)

    transition = last_status != status
    if transition:
        logging.info("transition %s -> %s", last_status, status)
        notify_mac(
            "Toll-free status changed",
            f"{last_status or 'unknown'} -> {status}",
        )

    fired = False
    fire_note = ""

    should_fire = status == "TWILIO_REJECTED" and (transition or args.force)
    if should_fire:
        if attempts >= max_resubmits and not args.force:
            fire_note = f"max auto-resubmits reached ({attempts}/{max_resubmits}); manual review needed"
            logging.warning(fire_note)
            notify_mac("Toll-free REJECTED — manual review needed", fire_note)
        elif not opt_in_url_reachable(patch.get("OptInImageUrls", "")):
            fire_note = f"OptInImageUrls not reachable: {patch.get('OptInImageUrls')!r}; bailing"
            logging.error(fire_note)
            notify_mac("Toll-free REJECTED — consent PNG missing", fire_note)
        elif args.dry_run:
            fire_note = "dry-run: would have fired patch"
            logging.info(fire_note)
        else:
            ok, body = fire_patch(sid, patch, key_sid, key_secret)
            if ok:
                attempts += 1
                fired = True
                fire_note = f"v2 patch fired (attempt {attempts}/{max_resubmits})"
                logging.info("%s\nresponse: %s", fire_note, body[:400])
                notify_mac("Toll-free v2 patch fired", fire_note)
            else:
                fire_note = f"patch POST failed: {body}"
                logging.error(fire_note)
                notify_mac("Toll-free patch FAILED", fire_note[:200])

    if status == "TWILIO_APPROVED" and last_status != "TWILIO_APPROVED":
        logging.info("APPROVED — celebrating")
        notify_mac(
            "Toll-free APPROVED 🎉",
            "+18886016132 is verified. mom.93.fyi can send SMS.",
        )

    state.update(
        last_status=status,
        last_checked=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        auto_resubmit_attempts=attempts,
        last_fire_note=fire_note,
        last_rejection_reasons=rejection_reasons,
        last_rejection_reason=rejection_reason,
        last_status_transition=transition,
        last_fired=fired,
    )
    save_state(state)
    logging.info("monitor end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
