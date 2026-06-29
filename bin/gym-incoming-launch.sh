#!/bin/bash
# Launcher for gym_incoming_pipeline.py.
#
# - Pulls GMAIL_APP_PASSWORD from Keychain (service: triage-gmail-app-password)
# - Bumps iogpu.wired_limit_mb to 30720 (via /etc/sudoers.d/karl-ramtune NOPASSWD)
# - Purges disk cache
# - Starts dedicated 27B server on :8084 (avoids conflict with watchdog :8080)
# - Launches the python pipeline detached, writes log + pid files
# - On exit (trap): kills 27B, reverts iogpu cap
#
# Logs:
#   ~/.local/share/gym-incoming-pipeline/run.log         — pipeline progress
#   ~/.local/share/gym-incoming-pipeline/27b-server.log  — mlx_vlm.server stdout/stderr
#   ~/.local/share/gym-incoming-pipeline/launcher.log    — this script's output
#
# Usage:  nohup ~/karl-infra/bin/gym-incoming-launch.sh >/dev/null 2>&1 &

set -u

OUT_DIR="$HOME/.local/share/gym-incoming-pipeline"
mkdir -p "$OUT_DIR"

LAUNCH_LOG="$OUT_DIR/launcher.log"
PIPE_LOG="$OUT_DIR/run.log"
SERVER_LOG="$OUT_DIR/27b-server.log"
PID_DIR="$OUT_DIR/pids"
mkdir -p "$PID_DIR"

exec >>"$LAUNCH_LOG" 2>&1
echo
echo "=== gym-incoming-launch START $(date '+%Y-%m-%d %H:%M:%S') ==="

# --- Gmail app password from Keychain ---
GMAIL_PW=$(security find-generic-password -a "$USER" -s triage-gmail-app-password -w 2>/dev/null || true)
if [ -z "$GMAIL_PW" ]; then
  echo "FAIL: GMAIL app password not found in Keychain service 'triage-gmail-app-password'"
  exit 1
fi
export GMAIL_USER="karlmarx9193@gmail.com"
export GMAIL_APP_PASSWORD="$GMAIL_PW"
export DIGEST_TO="karlmarx9193@gmail.com"
echo "Gmail credentials loaded ($GMAIL_USER → $DIGEST_TO)"

# --- Bump GPU wired cap & purge ---
echo "Bumping iogpu.wired_limit_mb to 30720..."
if sudo -n /usr/sbin/sysctl iogpu.wired_limit_mb=30720; then
  echo "  cap bumped"
else
  echo "  WARN: sudo -n failed; sudoers /etc/sudoers.d/karl-ramtune missing or expired? Continuing at OS-default cap."
fi

echo "Purging disk cache..."
sudo -n /usr/sbin/purge && echo "  purged" || echo "  WARN: purge failed"

# --- Start dedicated 27B server on :8084 ---
echo "Starting 27B on :8084..."
nohup "$HOME/.local/bin/mlx_vlm.server" \
  --model mlx-community/Qwen3.5-27B-4bit \
  --host 127.0.0.1 --port 8084 \
  >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_DIR/27b.pid"
echo "  27B server pid=$SERVER_PID"

# --- Trap: cleanup on exit ---
cleanup() {
  echo "--- cleanup $(date '+%H:%M:%S') ---"
  if [ -f "$PID_DIR/27b.pid" ]; then
    kill "$(cat "$PID_DIR/27b.pid")" 2>/dev/null && echo "  killed 27B"
    rm -f "$PID_DIR/27b.pid"
  fi
  sudo -n /usr/sbin/sysctl iogpu.wired_limit_mb=0 && echo "  reverted iogpu cap" || echo "  WARN: revert failed"
  echo "=== gym-incoming-launch END $(date '+%Y-%m-%d %H:%M:%S') ==="
}
trap cleanup EXIT INT TERM

# --- Run the pipeline (foreground; we are already detached via nohup) ---
echo "Launching pipeline..."
echo "  python: $HOME/.local/bin/uv run --quiet /Users/kmx/karl-infra/services/gym_incoming_pipeline.py"
"$HOME/.local/bin/uv" run --quiet /Users/kmx/karl-infra/services/gym_incoming_pipeline.py
PIPE_RC=$?
echo "pipeline exited with rc=$PIPE_RC"
exit $PIPE_RC
