"""Build the Status snapshot the phone reads (system + day fields)."""
from __future__ import annotations

import re
import socket
import subprocess
import time
from pathlib import Path


def port_up(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _total_ram_gb() -> float:
    out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout
    try:
        return int(out.strip()) / (1024**3)
    except ValueError:
        return 36.0


def _free_ram_pct() -> float:
    """True free-RAM percentage from `memory_pressure`.

    `top`'s "unused" figure underreports badly on a healthy Mac (RAM held in the
    compressor / file cache reads as "used"), so it always looked near-critical.
    `memory_pressure` reports the real system-wide free percentage.
    """
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    m = re.search(r"free percentage:\s*(\d+)%", out)
    return float(m.group(1)) if m else 0.0


def _free_ram_gb() -> float:
    return round(_free_ram_pct() / 100.0 * _total_ram_gb(), 1)


def classify_pressure(free_pct: float) -> str:
    """free_pct = percent of total RAM free (0-100)."""
    if free_pct >= 50:
        return "normal"
    if free_pct >= 20:
        return "warn"
    return "critical"


def _pt_today() -> str:
    hep = Path.home() / "Nextcloud" / "Documents" / "pt_today.txt"
    if hep.exists():
        return hep.read_text(encoding="utf-8").strip()[:200]
    return "No physical therapy items recorded for today, sir."


def _top_todos(n: int = 3) -> list[str]:
    todo = Path.home() / "Nextcloud" / "Documents" / "todo.md"
    if not todo.exists():
        return []
    items = [
        ln.strip("- [ ]").strip()
        for ln in todo.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("- [ ]")
    ]
    return items[:n]


def build_status() -> dict:
    free_pct = _free_ram_pct()
    return {
        "ts": int(time.time() * 1000),
        "ramFreeGb": round(free_pct / 100.0 * _total_ram_gb(), 1),
        "memPressure": classify_pressure(free_pct),
        "mlx8080": port_up(8080),
        "mlx8081": port_up(8081),
        "lastDeployAgeMin": None,
        "ptToday": _pt_today(),
        "todos": _top_todos(),
    }
