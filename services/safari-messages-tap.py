#!/usr/bin/env python3
"""Tap mom's Google Messages thread from Safari.

Reads the front Safari tab. If it's mom's thread on messages.google.com,
extracts the visible messages and appends new ones (deduped by msg-id) to
a rolling JSONL archive at ~/.claude/messages-context/mom.jsonl.

Run on demand:
    uv run ~/karl-infra/services/safari-messages-tap.py

Requires:
    - Safari running, paired with mom's phone, mom's thread open in front tab
    - Develop > "Allow JavaScript from Apple Events" enabled

Scope is intentionally narrow: only the thread whose URL starts with the
EXPECTED_URL_PREFIX below. To extend to other threads, take a URL prefix
as an argument and route to a per-thread JSONL.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ARCHIVE_DIR = Path.home() / ".claude" / "messages-context"
ARCHIVE_FILE = ARCHIVE_DIR / "mom.jsonl"
EXPECTED_URL_PREFIX = (
    "https://messages.google.com/web/conversations/CghFdeWfr4MJqRICMjI"
)
OSASCRIPT_TIMEOUT_S = 15


def osascript_safari(js_code: str) -> str:
    """Run JS in Safari's front document; return its string result."""
    js_literal = json.dumps(js_code)
    script = (
        'tell application "Safari"\n'
        f"  do JavaScript {js_literal} in front document\n"
        "end tell"
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=OSASCRIPT_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"osascript failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


EXTRACT_JS = """(() => {
  const wrappers = document.querySelectorAll('mws-message-wrapper');
  const out = [];
  for (const w of wrappers) {
    const id = w.getAttribute('msg-id') || '';
    const isOutgoing = w.getAttribute('is-outgoing') === 'true';
    const text = (w.innerText || '').trim();
    if (!id || !text) continue;
    out.push({ id, dir: isOutgoing ? 'out' : 'in', text });
  }
  return JSON.stringify(out);
})()"""


def main() -> int:
    try:
        url = osascript_safari("location.href")
    except Exception as e:
        sys.stderr.write(f"Could not read Safari: {e}\n")
        sys.stderr.write(
            "Is Safari running? Is Develop > 'Allow JavaScript from Apple Events' enabled?\n"
        )
        return 2

    if not url.startswith(EXPECTED_URL_PREFIX):
        sys.stderr.write(
            f"Front Safari tab is {url}\nExpected a URL starting with {EXPECTED_URL_PREFIX}\nNothing tapped.\n"
        )
        return 1

    raw = osascript_safari(EXTRACT_JS)
    new_msgs = json.loads(raw)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if ARCHIVE_FILE.exists():
        with ARCHIVE_FILE.open() as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["id"])
                except (KeyError, json.JSONDecodeError):
                    continue

    added = 0
    with ARCHIVE_FILE.open("a") as f:
        for m in new_msgs:
            if m["id"] in seen:
                continue
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            seen.add(m["id"])
            added += 1

    os.chmod(ARCHIVE_FILE, 0o600)

    print(
        f"Tapped Safari: {len(new_msgs)} messages visible. "
        f"Added {added} new. Archive {ARCHIVE_FILE} now holds {len(seen)} total."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
