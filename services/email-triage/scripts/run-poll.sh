#!/bin/bash
# Wrapper invoked by launchd. Runs one poll cycle and exits.
set -euo pipefail

cd "$(dirname "$0")/.."

# launchd ships with a minimal PATH. Include:
#   - $HOME/.local/bin where `uv` is installed by the official installer
#   - /opt/homebrew/bin + /usr/local/bin so `npx` (Gmail MCP) resolves
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# uv handles the virtualenv + deps. .env is loaded by the runner itself.
exec uv run -- python -m triage poll
