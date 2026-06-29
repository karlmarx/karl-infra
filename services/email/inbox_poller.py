#!/usr/bin/env python3
"""cld@93.fyi inbox poller — STUB.

Runs from LaunchAgent every N minutes. Reads Gmail label:cld/inbox unread
threads, applies the allowlist policy (option 3c), and either:

  AUTO-REPLY    for allowlisted senders → invoke sender.py with --from cld and
                --in-reply-to set from the original Message-ID
  NOTIFY-ONLY   for non-allowlisted senders → write structured JSON to
                ~/karl-infra/inbox/cld/<thread_id>.json + Discord ping

CURRENT STATE: stub only. Exits 0 with a single log line.

PENDING IMPLEMENTATION
- Standalone Gmail API access (the claude.ai Gmail MCP only works inside
  Claude Code sessions; this script runs from launchd). Options:
    a) IMAP with an app-password
    b) google-api-python-client + a separate gmail.readonly OAuth token
- Discord webhook (check ~/.openclaw/openclaw.json for one, else add)
- Auto-reply generation — likely shells out to `openclaw infer agent run`
  with a cld-triage prompt; OR writes a pending file the user processes
  on next Claude session.
"""

import sys
from datetime import datetime

print(f"{datetime.now().isoformat()} cld-watch: STUB — implementation pending")
sys.exit(0)
