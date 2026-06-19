#!/bin/bash
# Wrapper invoked by launchd. Runs one outreach cycle and exits.
# launchd re-invokes us on schedule (default: every 4 hours).
set -euo pipefail

cd "$(dirname "$0")/.."

# Homebrew Python / Playwright Chromium paths.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

exec uv run -- python -m outreach run
