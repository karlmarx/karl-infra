#!/usr/bin/env python3
"""VLM background-pipeline progress digest.

Snapshots state of `continuous_process.py` (videos catalogued, GIFs produced,
worker iteration markers, recent log tail). Writes a Markdown summary to
Nextcloud Documents — auto-syncs to Karl's phone via the Nextcloud app.

Optionally emails the digest if GMAIL_APP_PASSWORD is set (mirrors the
workout_digest.py pattern). When the password is the placeholder string,
the email is skipped silently — the markdown still ships to Nextcloud.

Designed to be invoked by launchd every few hours. Idempotent: state is
tracked in `~/.local/share/vlm-progress/last-digest-state.json`.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil"]
# ///

import json
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import psutil


PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
LOG_DIR = Path.home() / ".local/share/local-vlm-analysis"
NEXTCLOUD = Path.home() / "Nextcloud" / "Documents"
STATE_FILE = Path.home() / ".local/share/vlm-progress/last-digest-state.json"

DASHBOARD_REPO = Path.home() / "karl-command-center"
DASHBOARD_JSON = DASHBOARD_REPO / "public" / "vlm-status.json"
PUBLISH_DASHBOARD = os.environ.get("PUBLISH_DASHBOARD", "1") != "0"

GMAIL_USER = os.environ.get("GMAIL_USER", "karlmarx9193@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
DIGEST_TO = os.environ.get("DIGEST_TO", "karlmarx9193@gmail.com")
PLACEHOLDER = "FILL_IN_FROM_KEEPASS"


def collect_state() -> dict:
    """Snapshot the current state of the VLM pipeline."""
    videos_dir = PROJECT / "data" / "videos"
    gifs_dir = PROJECT / "data" / "gifs"
    manifest_path = gifs_dir / "_manifest.json"

    video_count = sum(1 for _ in videos_dir.glob("*.json")) if videos_dir.exists() else 0
    gif_paths = list(gifs_dir.rglob("*.gif")) if gifs_dir.exists() else []
    gif_count = len(gif_paths)

    manifest = {}
    try:
        manifest = json.loads(manifest_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    exercises = manifest.get("exercises", {})

    latest_log = None
    last_iteration = None
    last_processed = None
    last_log_mtime = None
    if LOG_DIR.exists():
        logs = sorted(LOG_DIR.glob("continuous-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            latest_log = logs[0]
            last_log_mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)
            tail_lines = latest_log.read_text(errors="replace").splitlines()[-300:]
            for line in tail_lines:
                if "--- Iteration" in line:
                    last_iteration = line.strip()
                if "Total videos processed" in line:
                    last_processed = line.strip()

    worker_running = False
    worker_pid = None
    worker_etime = None
    for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
        try:
            cmd = proc.info.get("cmdline") or []
            if any("continuous_process.py" in c for c in cmd):
                worker_running = True
                worker_pid = proc.info["pid"]
                worker_etime = datetime.now() - datetime.fromtimestamp(proc.info["create_time"])
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    vm = psutil.virtual_memory()

    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "video_count": video_count,
        "gif_count": gif_count,
        "exercises": {k: len(v) for k, v in exercises.items()},
        "manifest_generated_at": manifest.get("generated_at"),
        "last_iteration": last_iteration,
        "last_processed": last_processed,
        "last_log_path": str(latest_log) if latest_log else None,
        "last_log_mtime": last_log_mtime.isoformat() if last_log_mtime else None,
        "worker_running": worker_running,
        "worker_pid": worker_pid,
        "worker_uptime": _fmt_timedelta(worker_etime) if worker_etime else None,
        "ram_available_gb": round(vm.available / 1024**3, 2),
        "ram_percent_used": vm.percent,
    }


def _fmt_timedelta(td) -> str:
    """h/m/s format suitable for status lines."""
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h >= 24:
        d, h = divmod(h, 24)
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def compute_delta(prev: dict | None, curr: dict) -> dict:
    if not prev:
        return {"first_run": True}
    return {
        "first_run": False,
        "videos_delta": curr["video_count"] - prev.get("video_count", 0),
        "gifs_delta": curr["gif_count"] - prev.get("gif_count", 0),
        "exercises_delta": _diff_exercise_counts(prev.get("exercises", {}), curr["exercises"]),
        "since": prev.get("ts", "?"),
    }


def _diff_exercise_counts(prev: dict, curr: dict) -> dict:
    out = {}
    for k, v in curr.items():
        delta = v - prev.get(k, 0)
        if delta:
            out[k] = delta
    return out


def render_markdown(state: dict, delta: dict, log_tail: list[str]) -> str:
    lines = [
        "# VLM background progress",
        f"_{state['ts']}_",
        "",
        "## Snapshot",
        f"- Videos catalogued: **{state['video_count']}**",
    ]
    if not delta.get("first_run"):
        sign = "+" if delta["videos_delta"] >= 0 else ""
        lines.append(f"  - Δ since {delta['since']}: **{sign}{delta['videos_delta']}**")
    lines.append(f"- Exercise GIFs: **{state['gif_count']}** across {len(state['exercises'])} exercises")
    if not delta.get("first_run") and delta.get("gifs_delta"):
        sign = "+" if delta["gifs_delta"] >= 0 else ""
        lines.append(f"  - Δ: **{sign}{delta['gifs_delta']}**")
    lines.extend([
        f"- Worker: {'running' if state['worker_running'] else '**STOPPED**'}"
        + (f" (PID {state['worker_pid']}, up {state['worker_uptime']})" if state['worker_running'] else ""),
        f"- RAM available: {state['ram_available_gb']} GB ({state['ram_percent_used']}% used)",
    ])

    if delta.get("exercises_delta"):
        lines.extend(["", "## New since last digest"])
        for name, delta_n in sorted(delta["exercises_delta"].items(), key=lambda x: -x[1]):
            sign = "+" if delta_n >= 0 else ""
            lines.append(f"- {name}: {sign}{delta_n}")

    if state["exercises"]:
        lines.extend(["", "## Exercises (gif count)"])
        for name, cnt in sorted(state["exercises"].items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {name}: {cnt}")

    lines.extend([
        "",
        "## Worker iteration markers",
        f"- {state['last_iteration']}" if state["last_iteration"] else "- (no iteration markers found)",
        f"- {state['last_processed']}" if state["last_processed"] else "",
        f"- Last log update: {state['last_log_mtime']}",
    ])

    if log_tail:
        lines.extend(["", "## Recent log tail", "```"])
        lines.extend(log_tail)
        lines.append("```")

    lines.extend(["", "Browse gallery: <https://hot.93.fyi/>"])
    return "\n".join(line for line in lines if line is not None)


def render_html(md: str) -> str:
    escaped = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:680px;margin:1.5rem auto;line-height:1.5'>"
        f"<pre style='white-space:pre-wrap;font-family:inherit'>{escaped}</pre>"
        "</body></html>"
    )


def write_nextcloud(md: str) -> Path:
    NEXTCLOUD.mkdir(parents=True, exist_ok=True)
    latest = NEXTCLOUD / "vlm-progress.md"
    latest.write_text(md)

    history = NEXTCLOUD / "vlm-progress-history.md"
    header = f"\n\n---\n\n"
    if history.exists():
        history.write_text(history.read_text() + header + md)
    else:
        history.write_text("# VLM progress history\n" + header + md)
    return latest


def publish_dashboard(state: dict, delta: dict, log_tail: list[str]) -> tuple[bool, str]:
    """Write the rich JSON to karl-command-center/public/ and git-push it.

    Vercel auto-deploys on push. Skip if no actual change to the JSON content
    so we don't churn deployments.
    """
    if not PUBLISH_DASHBOARD:
        return False, "PUBLISH_DASHBOARD=0"
    if not DASHBOARD_REPO.exists():
        return False, f"{DASHBOARD_REPO} not found"

    payload = {
        "ts": state["ts"],
        "video_count": state["video_count"],
        "gif_count": state["gif_count"],
        "exercises": state["exercises"],
        "manifest_generated_at": state["manifest_generated_at"],
        "worker_running": state["worker_running"],
        "worker_pid": state["worker_pid"],
        "worker_uptime": state["worker_uptime"],
        "last_iteration": state["last_iteration"],
        "last_processed": state["last_processed"],
        "last_log_mtime": state["last_log_mtime"],
        "ram_available_gb": state["ram_available_gb"],
        "ram_percent_used": state["ram_percent_used"],
        "delta": delta,
        "log_tail": log_tail,
        "gallery_url": "https://hot.93.fyi/",
    }

    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    new_content = json.dumps(payload, indent=2) + "\n"

    # Skip git work if content unchanged (avoids no-op deploys)
    if DASHBOARD_JSON.exists() and DASHBOARD_JSON.read_text() == new_content:
        return True, "unchanged"

    DASHBOARD_JSON.write_text(new_content)

    try:
        subprocess.run(
            ["git", "-C", str(DASHBOARD_REPO), "add", "public/vlm-status.json"],
            check=True, capture_output=True, text=True, timeout=15,
        )
        # Empty commit guard — only commit if actually staged
        diff = subprocess.run(
            ["git", "-C", str(DASHBOARD_REPO), "diff", "--cached", "--quiet"],
        )
        if diff.returncode == 0:
            return True, "no staged change"

        msg = f"data: vlm-status {datetime.now():%Y-%m-%dT%H:%M}"
        subprocess.run(
            ["git", "-C", str(DASHBOARD_REPO), "commit", "-m", msg],
            check=True, capture_output=True, text=True, timeout=15,
        )
        push = subprocess.run(
            ["git", "-C", str(DASHBOARD_REPO), "push", "origin", "HEAD"],
            capture_output=True, text=True, timeout=60,
        )
        if push.returncode != 0:
            return False, f"push failed: {push.stderr.strip()[:200]}"
        return True, f"pushed: {msg}"
    except subprocess.CalledProcessError as e:
        return False, f"git error: {e.stderr.strip()[:200] if e.stderr else e}"
    except subprocess.TimeoutExpired:
        return False, "git operation timed out"


def send_email(md: str, html: str) -> tuple[bool, str]:
    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD == PLACEHOLDER:
        return False, "GMAIL_APP_PASSWORD not configured (placeholder or empty)"
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_USER
        msg["To"] = DIGEST_TO
        msg["Subject"] = f"VLM progress — {datetime.now():%a %H:%M}"
        msg.attach(MIMEText(md, "plain"))
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [DIGEST_TO], msg.as_string())
        return True, f"sent to {DIGEST_TO}"
    except Exception as e:
        return False, f"smtp error: {e!r}"


def load_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return None
    return None


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def collect_log_tail(n: int = 30) -> list[str]:
    if not LOG_DIR.exists():
        return []
    logs = sorted(LOG_DIR.glob("continuous-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return []
    return logs[0].read_text(errors="replace").splitlines()[-n:]


def main() -> int:
    prev = load_state()
    curr = collect_state()
    delta = compute_delta(prev, curr)
    log_tail = collect_log_tail(30)

    md = render_markdown(curr, delta, log_tail)
    nc_path = write_nextcloud(md)

    email_ok, email_msg = send_email(md, render_html(md))
    dash_ok, dash_msg = publish_dashboard(curr, delta, log_tail)

    save_state(curr)

    print(f"[{datetime.now():%H:%M:%S}] digest written: {nc_path}")
    print(f"  videos={curr['video_count']} gifs={curr['gif_count']} worker={'up' if curr['worker_running'] else 'DOWN'}")
    if not delta.get("first_run"):
        print(f"  delta: videos={delta['videos_delta']:+d} gifs={delta['gifs_delta']:+d}")
    print(f"  email: {'✓ sent' if email_ok else '✗ skipped'} — {email_msg}")
    print(f"  dashboard: {'✓' if dash_ok else '✗'} — {dash_msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
