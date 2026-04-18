#!/usr/bin/env python
"""
Background Process Monitor Dashboard

Real-time terminal UI for monitoring all Mac Studio background processes:
- Nextcloud photo sync (hourly)
- Screenshot parser + TODO creation (hourly)
- Return receipt scanner (6h interval)
- Photo memory pipeline (on-demand)
- Any LaunchAgent/cron jobs

Pure Python with no external dependencies
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import re
import time
import os

@dataclass
class ProcessInfo:
    """Information about a background process."""
    name: str
    status: str  # "running", "idle", "error", "pending"
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    interval: str  # "hourly", "6h", "on-demand", etc.
    log_file: Optional[Path]
    error_count: int = 0
    last_error: Optional[str] = None

class ProcessMonitor:
    """Monitor and display background processes."""

    def __init__(self):
        self.processes: List[ProcessInfo] = []
        self.update_interval = 5  # seconds
        self.load_processes()

    def load_processes(self):
        """Discover and configure all background processes."""
        self.processes = [
            ProcessInfo(
                name="Nextcloud Photo Sync",
                status="idle",
                last_run=None,
                next_run=None,
                interval="hourly",
                log_file=Path.home() / ".local/share/nextcloud-sync/sync.log"
            ),
            ProcessInfo(
                name="Screenshot Parser",
                status="idle",
                last_run=None,
                next_run=None,
                interval="hourly",
                log_file=Path.home() / ".local/share/nextcloud-sync/screenshot-parser.log"
            ),
            ProcessInfo(
                name="Return Receipt Scanner",
                status="idle",
                last_run=None,
                next_run=None,
                interval="6h",
                log_file=Path.home() / ".local/share/return-scanner/scanner.log"
            ),
            ProcessInfo(
                name="Photo Memory Pipeline",
                status="idle",
                last_run=None,
                next_run=None,
                interval="on-demand",
                log_file=Path.home() / ".local/share/photo-memory/pipeline.log"
            ),
        ]

        # Update status from logs
        for proc in self.processes:
            self.update_process_status(proc)

    def update_process_status(self, proc: ProcessInfo):
        """Update process status from log file and LaunchAgent."""
        if not proc.log_file or not proc.log_file.exists():
            proc.status = "pending"
            return

        try:
            # Read last few lines of log
            with open(proc.log_file, "r") as f:
                lines = f.readlines()

            if lines:
                last_line = lines[-1].strip()

                # Parse timestamp and status from log
                if "ERROR" in last_line:
                    proc.status = "error"
                    proc.last_error = last_line[-80:]  # Last 80 chars
                    proc.error_count += 1
                elif "successfully" in last_line.lower() or "complete" in last_line.lower():
                    proc.status = "idle"
                elif "Starting" in last_line or "Processing" in last_line:
                    proc.status = "running"

                # Extract timestamp
                match = re.search(r'\[([^\]]+)\]', last_line)
                if match:
                    try:
                        proc.last_run = datetime.fromisoformat(match.group(1))
                        # Calculate next run based on interval
                        if proc.interval == "hourly":
                            proc.next_run = proc.last_run + timedelta(hours=1)
                        elif proc.interval == "6h":
                            proc.next_run = proc.last_run + timedelta(hours=6)
                    except:
                        pass

        except Exception as e:
            proc.status = "error"
            proc.last_error = str(e)

    def get_launchctl_status(self, label: str) -> str:
        """Check if LaunchAgent is loaded."""
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "loaded" if label in result.stdout else "unloaded"
        except:
            return "unknown"

    def render_ascii(self):
        """Render dashboard as ASCII table (no external deps)."""
        os.system('clear' if os.name == 'posix' else 'cls')

        print("\n" + "="*100)
        print("🖥️  BACKGROUND PROCESS MONITOR".center(100))
        print("="*100 + "\n")

        # Header row
        header = f"{'Process':<25} {'Status':<12} {'Last Run':<19} {'Next Run':<19} {'Interval':<10}"
        print(header)
        print("-"*100)

        # Process rows
        for proc in self.processes:
            if proc.status == "running":
                status = "⚡ RUNNING"
            elif proc.status == "error":
                status = "❌ ERROR"
            elif proc.status == "idle":
                status = "✓ Idle"
            else:
                status = "⊙ Pending"

            last_run = proc.last_run.strftime("%Y-%m-%d %H:%M") if proc.last_run else "never"
            next_run = proc.next_run.strftime("%Y-%m-%d %H:%M") if proc.next_run else "N/A"

            row = f"{proc.name:<25} {status:<12} {last_run:<19} {next_run:<19} {proc.interval:<10}"
            print(row)

        print("-"*100)

        # Summary stats
        errors = sum(1 for p in self.processes if p.status == "error")
        running = sum(1 for p in self.processes if p.status == "running")
        idle = sum(1 for p in self.processes if p.status == "idle")

        print(f"\n✓ Idle: {idle}  |  ⚡ Running: {running}  |  ❌ Errors: {errors}")
        print(f"\nLast update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refresh: {self.update_interval}s")
        print("\nCommands: [r] refresh  [l] show logs  [e] errors  [q] quit")
        print("\n" + "="*100 + "\n")

    def run(self):
        """Run the dashboard in loop."""
        try:
            while True:
                self.render_ascii()
                # Update all process statuses
                for proc in self.processes:
                    self.update_process_status(proc)
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            print("\n[✓] Dashboard stopped\n")

def main():
    """Launch the dashboard."""
    monitor = ProcessMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
