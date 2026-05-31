"""Concrete Mac action handlers, registered by key."""
from __future__ import annotations

import os
import subprocess

from registry import register


def _run(cmd: list[str]) -> bool:
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


@register("restart_sync")
def restart_sync(intent) -> str:
    ok = _run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.karlmarx.nextcloud-sync"])
    return "Photo sync restarted, sir." if ok else "I could not restart the photo sync, sir."


@register("restart_photo")
def restart_photo(intent) -> str:
    ok = _run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.karlmarx.photo-memory"])
    return "Photo memory pipeline restarted, sir." if ok else "The photo memory pipeline would not restart, sir."


@register("resume_jobs")
def resume_jobs(intent) -> str:
    """SIGCONT any watchdog-paused local-batch processes (matched by name)."""
    out = subprocess.run(["pgrep", "-f", "gym_|vlm_|photo-memory"], capture_output=True, text=True)
    pids = [p for p in out.stdout.split() if p]
    for pid in pids:
        subprocess.run(["kill", "-CONT", pid], check=False)
    return f"Resumed {len(pids)} paused jobs, sir." if pids else "There were no paused jobs to resume, sir."


@register("wake")
def wake(intent) -> str:
    subprocess.run(["caffeinate", "-u", "-t", "2"], check=False)
    return "The Mac is awake, sir."
