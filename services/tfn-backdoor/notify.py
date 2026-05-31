"""macOS notification + Discord webhook. Never raises."""
from __future__ import annotations

import os
import subprocess

import requests


def _webhook() -> str | None:
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ["USER"], "-s", "nwb-tfn-notify-webhook", "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def notify(message: str) -> None:
    try:
        subprocess.run(["terminal-notifier", "-title", "tfn-backdoor", "-message", message], check=False)
    except Exception:
        pass
    url = _webhook()
    if url:
        try:
            requests.post(url, json={"content": f"📞 tfn-backdoor (mac): {message}"}, timeout=5)
        except Exception:
            pass
