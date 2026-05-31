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


def _free_ram_gb() -> float:
    """Parse `top -l1 | grep PhysMem` -> unused GB."""
    out = subprocess.run(["top", "-l1"], capture_output=True, text=True).stdout
    m = re.search(r"PhysMem:.*?(\d+)([MG]) unused", out)
    if not m:
        return 0.0
    val, unit = float(m.group(1)), m.group(2)
    return val if unit == "G" else val / 1024.0


def classify_pressure(free_gb_pct: float) -> str:
    """free_gb_pct = percent of total RAM free (0-100)."""
    if free_gb_pct >= 50:
        return "normal"
    if free_gb_pct >= 20:
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
    total_gb = 36.0
    free = _free_ram_gb()
    pressure = classify_pressure(free / total_gb * 100)
    return {
        "ts": int(time.time() * 1000),
        "ramFreeGb": round(free, 1),
        "memPressure": pressure,
        "mlx8080": port_up(8080),
        "mlx8081": port_up(8081),
        "lastDeployAgeMin": None,
        "ptToday": _pt_today(),
        "todos": _top_todos(),
    }
