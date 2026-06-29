#!/usr/bin/env bash
# OpenClaw gateway launcher: fetches secrets from Keychain → exports env → execs node.
#
# Pinned as the `-T` trusted reader for the following Keychain services:
#   openclaw-github-token
#   openclaw-gemini-api-key
#   openclaw-google-api-key
#   openclaw-keepass-master
#   openclaw-paperclip-api-key
#   openclaw-gateway-auth-token
#   openclaw-telegram-bot-token
#   openclaw-discord-token
#
# Replacing or modifying this script will cause Keychain to revoke the trust
# and prompt for approval on the next read.

set -euo pipefail

LOG_PREFIX="[openclaw-loader $(date +%H:%M:%S)]"

get_secret() {
  local name="$1"
  local value
  if value=$(security find-generic-password -a "$USER" -s "$name" -w 2>/dev/null); then
    printf '%s' "$value"
  else
    echo "${LOG_PREFIX} FATAL: Keychain entry '${name}' not found or unreadable" >&2
    return 1
  fi
}

# Fetch all 8 secrets up front so we fail fast if any are missing.
GITHUB_TOKEN=$(get_secret openclaw-github-token)
GEMINI_API_KEY=$(get_secret openclaw-gemini-api-key)
GOOGLE_API_KEY=$(get_secret openclaw-google-api-key)
KEEPASS_MASTER_PASSWORD=$(get_secret openclaw-keepass-master)
PAPERCLIP_API_KEY=$(get_secret openclaw-paperclip-api-key)
OPENCLAW_GATEWAY_AUTH_TOKEN=$(get_secret openclaw-gateway-auth-token)
TELEGRAM_BOT_TOKEN=$(get_secret openclaw-telegram-bot-token)
DISCORD_BOT_TOKEN=$(get_secret openclaw-discord-token)

export GITHUB_TOKEN GEMINI_API_KEY GOOGLE_API_KEY KEEPASS_MASTER_PASSWORD \
       PAPERCLIP_API_KEY OPENCLAW_GATEWAY_AUTH_TOKEN \
       TELEGRAM_BOT_TOKEN DISCORD_BOT_TOKEN

echo "${LOG_PREFIX} loaded 8 secrets from Keychain; execing gateway" >&2

# Allow dry-run verification: `openclaw-gateway-loader.sh --check` reports
# success without spawning node. Used during migration & post-rotation testing.
if [ "${1:-}" = "--check" ]; then
  echo "${LOG_PREFIX} --check OK: all 8 secrets resolved" >&2
  exit 0
fi

exec /opt/homebrew/bin/node \
  /Users/kmx/.nvm/versions/node/v24.11.1/lib/node_modules/openclaw/dist/index.js \
  gateway --port 18789
