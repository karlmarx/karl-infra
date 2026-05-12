#!/bin/bash
# Wrapper invoked by launchd. Runs one poll cycle and exits.
set -euo pipefail

cd "$(dirname "$0")/.."

# Pick up a couple common Homebrew Node paths so the MCP server can be spawned.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# uv handles the virtualenv + deps. .env is loaded by the runner itself.
exec uv run -- python -m triage poll
