#!/bin/bash
# Launcher for gym_attraction_rescore.py.
# Same pattern as gym-incoming-launch.sh: Keychain creds, sudo iogpu bump,
# dedicated 27B on :8084, trap cleanup. Pipeline operates on the existing
# ~/.local/share/gym-2month-pipeline/ outputs — no new GIF generation.

set -u

OUT_DIR="$HOME/.local/share/gym-attraction-rescore"
mkdir -p "$OUT_DIR" "$OUT_DIR/pids"

LAUNCH_LOG="$OUT_DIR/launcher.log"
SERVER_LOG="$OUT_DIR/27b-server.log"

exec >>"$LAUNCH_LOG" 2>&1
echo
echo "=== gym-attraction-rescore-launch START $(date '+%Y-%m-%d %H:%M:%S') ==="

GMAIL_PW=$(security find-generic-password -a "$USER" -s triage-gmail-app-password -w 2>/dev/null || true)
if [ -z "$GMAIL_PW" ]; then
  echo "FAIL: GMAIL app password not found in Keychain service 'triage-gmail-app-password'"
  exit 1
fi
export GMAIL_USER="karlmarx9193@gmail.com"
export GMAIL_APP_PASSWORD="$GMAIL_PW"
export DIGEST_TO="karlmarx9193@gmail.com"
echo "Gmail credentials loaded"

echo "Bumping iogpu.wired_limit_mb to 30720..."
sudo -n /usr/sbin/sysctl iogpu.wired_limit_mb=30720 && echo "  cap bumped" || echo "  WARN: cap bump failed"
sudo -n /usr/sbin/purge && echo "  purged" || echo "  WARN: purge failed"

echo "Starting 27B on :8084..."
nohup "$HOME/.local/bin/mlx_vlm.server" \
  --model mlx-community/Qwen3.5-27B-4bit \
  --host 127.0.0.1 --port 8084 \
  >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$OUT_DIR/pids/27b.pid"
echo "  27B server pid=$SERVER_PID"

cleanup() {
  echo "--- cleanup $(date '+%H:%M:%S') ---"
  if [ -f "$OUT_DIR/pids/27b.pid" ]; then
    kill "$(cat "$OUT_DIR/pids/27b.pid")" 2>/dev/null && echo "  killed 27B"
    rm -f "$OUT_DIR/pids/27b.pid"
  fi
  sudo -n /usr/sbin/sysctl iogpu.wired_limit_mb=0 && echo "  reverted iogpu cap" || echo "  WARN: revert failed"
  echo "=== gym-attraction-rescore-launch END $(date '+%Y-%m-%d %H:%M:%S') ==="
}
trap cleanup EXIT INT TERM

echo "Launching rescore pipeline..."
"$HOME/.local/bin/uv" run --quiet /Users/kmx/karl-infra/services/gym_attraction_rescore.py
PIPE_RC=$?
echo "pipeline exited with rc=$PIPE_RC"
exit $PIPE_RC
