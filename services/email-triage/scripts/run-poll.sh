#!/bin/bash
# Wrapper invoked by launchd. Runs one poll cycle and exits.
set -euo pipefail

cd "$(dirname "$0")/.."

# launchd gives us a bare PATH. $HOME/.local/bin is where `uv` installs itself
# on macOS; Homebrew dirs are needed for `npx` (if the MCP Gmail path is used).
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# uv handles the virtualenv + deps. .env is loaded by the runner itself.
exec uv run -- python -m triage poll
