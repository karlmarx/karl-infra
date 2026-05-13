#!/bin/bash
# Wrapper invoked by launchd. Polls Gmail IMAP for firm replies and updates state.
set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

exec uv run -- python -m outreach scan-replies
