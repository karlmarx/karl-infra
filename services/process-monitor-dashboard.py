#!/usr/bin/env python3
"""
Process Monitor Dashboard - Textual TUI

Modern terminal dashboard for monitoring:
- Background processes (Nextcloud, screenshot parser, etc.)
- Local LLM stats (Ollama models, VRAM usage)
- Claude session activity and memory usage

Uses Textual framework for professional sleek appearance with mouse support,
animations, and responsive layout.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict
import re
import time
import os

from textual.app import ComposeResult, App
from textual.widgets import (
    Header,
    Footer,
    Static,
    DataTable,
    Tabs,
    TabPane,
    Label,
)
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
import asyncio


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


@dataclass
class OllamaModel:
    """Information about a loaded Ollama model."""
    name: str
    size_mb: float
    loaded: bool
    last_used: Optional[datetime] = None


@dataclass
class ClaudeSession:
    """Information about a Claude session."""
    name: str
    path: Path
    size_mb: float
    last_modified: datetime
    token_estimate: int = 0


class ProcessMonitor:
    """Core monitor logic for processes, LLM activity, and Claude sessions."""

    def __init__(self):
        self.processes: List[ProcessInfo] = []
        self.ollama_models: List[OllamaModel] = []
        self.claude_sessions: List[ClaudeSession] = []
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
        """Update process status from log file."""
        if not proc.log_file or not proc.log_file.exists():
            proc.status = "pending"
            return

        try:
            with open(proc.log_file, "r") as f:
                lines = f.readlines()

            if lines:
                last_line = lines[-1].strip()

                if "ERROR" in last_line:
                    proc.status = "error"
                    proc.last_error = last_line[-80:]
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
                        if proc.interval == "hourly":
                            proc.next_run = proc.last_run + timedelta(hours=1)
                        elif proc.interval == "6h":
                            proc.next_run = proc.last_run + timedelta(hours=6)
                    except:
                        pass

        except Exception as e:
            proc.status = "error"
            proc.last_error = str(e)

    def get_ollama_stats(self) -> List[OllamaModel]:
        """Get Ollama running models and available models."""
        models = []

        try:
            # Get currently running models
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )

            running_models = set()
            if result.stdout and "NAME" in result.stdout:
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            running_models.add(parts[0])
        except:
            running_models = set()

        try:
            # Get all available models
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout and "NAME" in result.stdout:
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            name = parts[0]
                            size_str = f"{parts[2]} {parts[3]}"
                            size_mb = self._parse_size(size_str)
                            loaded = name in running_models

                            models.append(OllamaModel(
                                name=name,
                                size_mb=size_mb,
                                loaded=loaded
                            ))
        except:
            pass

        # Sort by size, loaded first
        models.sort(key=lambda m: (-m.loaded, -m.size_mb))
        return models

    def _parse_size(self, size_str: str) -> float:
        """Parse size string like '17 GB' or '9.6 GB' to MB."""
        try:
            size_str = size_str.strip()
            match = re.search(r'([\d.]+)\s*(GB|MB|KB|B)', size_str, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).upper()
                if unit == "GB":
                    return value * 1024
                elif unit == "MB":
                    return value
                elif unit == "KB":
                    return value / 1024
                elif unit == "B":
                    return value / (1024 * 1024)

            parts = size_str.split()
            if len(parts) >= 2:
                value = float(parts[0])
                unit = parts[1].upper()
                if unit == "GB":
                    return value * 1024
                elif unit == "MB":
                    return value
                elif unit == "KB":
                    return value / 1024

            return float(size_str)
        except:
            return 0.0

    def get_claude_sessions(self) -> List[ClaudeSession]:
        """Get recent Claude sessions from ~/.claude/projects."""
        sessions = []
        projects_dir = Path.home() / ".claude" / "projects"

        if not projects_dir.exists():
            return sessions

        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            for item in projects_dir.iterdir():
                if not item.is_dir():
                    continue

                try:
                    size_mb = self._get_dir_size(item) / (1024 * 1024)
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)

                    if mtime >= week_ago:
                        display_name = item.name.replace("-Users-kmx-", "").replace("-", "/")
                        if len(display_name) > 30:
                            display_name = display_name[:27] + "..."

                        token_estimate = int(size_mb * 400)

                        sessions.append(ClaudeSession(
                            name=display_name,
                            path=item,
                            size_mb=size_mb,
                            last_modified=mtime,
                            token_estimate=token_estimate
                        ))
                except:
                    pass

            sessions.sort(key=lambda s: s.last_modified, reverse=True)
            return sessions[:5]
        except:
            return sessions

    def _get_dir_size(self, path: Path) -> int:
        """Calculate directory size in bytes."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except:
                        pass
        except:
            pass
        return total

    def _format_timedelta(self, delta: timedelta) -> str:
        """Format timedelta as readable string."""
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600}h"
        else:
            return f"{total_seconds // 86400}d"


class ProcessesTable(DataTable):
    """Background processes table."""

    def on_mount(self) -> None:
        self.add_columns(
            "Name",
            "Status",
            "Last Run",
            "Next Run",
            "Interval",
        )


class OllamaTable(DataTable):
    """Ollama models table."""

    def on_mount(self) -> None:
        self.add_columns(
            "Model",
            "Size",
            "Status",
            "Loaded",
        )


class ClaudeTable(DataTable):
    """Claude sessions table."""

    def on_mount(self) -> None:
        self.add_columns(
            "Session",
            "Size",
            "Last Modified",
            "Tokens",
            "Activity",
        )


class StatusBar(Static):
    """Footer status bar with stats and key bindings."""

    def render(self) -> str:
        return "🔄 Refresh: 5s | [r] Force Refresh | [l] Logs | [?] Help | [q] Quit"


class ProcessMonitorApp(App):
    """Main Textual application for process monitor dashboard."""

    TITLE = "Process Monitor Dashboard"
    SUB_TITLE = "System Activity · LLM Stats · Claude Sessions"

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("l", "toggle_logs", "Logs", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    CSS = """
    Screen {
        background: $surface;
        color: $text;
    }

    Header {
        dock: top;
        height: 3;
        background: $boost;
        color: $text;
        border-bottom: solid $accent;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text;
        border-top: solid $accent;
    }

    #main-container {
        height: 1fr;
        border: none;
    }

    Tabs {
        height: 1fr;
        background: $surface;
        border: none;
    }

    TabPane {
        border: solid $accent;
        padding: 1 2;
    }

    DataTable {
        height: 1fr;
        border: solid $accent;
    }

    .section-title {
        width: 1fr;
        height: auto;
        color: $primary;
        text-style: bold;
        background: $boost;
        padding: 0 1;
        border-bottom: solid $accent;
    }

    .stats-box {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        background: $panel;
    }

    .stat-line {
        width: 1fr;
        color: $text;
    }

    .error {
        color: $error;
    }

    .warning {
        color: $warning;
    }

    .success {
        color: $success;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $panel;
        border-top: solid $accent;
        color: $text;
    }
    """

    def __init__(self):
        super().__init__()
        self.monitor = ProcessMonitor()
        self.last_update = datetime.now()
        self.update_counter = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            with Tabs(id="main-tabs"):
                with TabPane("⚡ Processes", id="processes-tab"):
                    yield ProcessesTable(id="processes-table")
                    yield Container(id="processes-stats")

                with TabPane("🤖 Ollama", id="ollama-tab"):
                    yield OllamaTable(id="ollama-table")
                    yield Container(id="ollama-stats")

                with TabPane("💬 Claude", id="claude-tab"):
                    yield ClaudeTable(id="claude-table")
                    yield Container(id="claude-stats")

        yield Footer()
        yield Static(id="status-bar", classes="stats-box")

    def on_mount(self) -> None:
        """Initialize app on mount."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        self._update_all_data()
        self.set_interval(5, self._update_all_data)

    async def _update_all_data(self) -> None:
        """Update all data tables and stats."""
        # Update processes
        for proc in self.monitor.processes:
            self.monitor.update_process_status(proc)
        self._update_processes_table()
        self._update_processes_stats()

        # Update Ollama
        self.monitor.ollama_models = self.monitor.get_ollama_stats()
        self._update_ollama_table()
        self._update_ollama_stats()

        # Update Claude sessions
        self.monitor.claude_sessions = self.monitor.get_claude_sessions()
        self._update_claude_table()
        self._update_claude_stats()

        # Update status bar
        self._update_status_bar()

        self.last_update = datetime.now()
        self.update_counter += 1

    def _update_processes_table(self) -> None:
        """Update processes DataTable."""
        table = self.query_one("#processes-table", ProcessesTable)
        table.clear()

        for proc in self.monitor.processes:
            status_display = self._get_status_emoji(proc.status) + " " + proc.status.upper()

            last_run_str = ""
            if proc.last_run:
                ago = datetime.now() - proc.last_run
                last_run_str = self.monitor._format_timedelta(ago) + " ago"

            next_run_str = ""
            if proc.next_run:
                until = proc.next_run - datetime.now()
                if until.total_seconds() > 0:
                    next_run_str = "in " + self.monitor._format_timedelta(until)
                else:
                    next_run_str = "now"

            table.add_row(
                proc.name,
                status_display,
                last_run_str,
                next_run_str,
                proc.interval,
            )

    def _update_processes_stats(self) -> None:
        """Update processes summary stats."""
        container = self.query_one("#processes-stats", Container)
        container.remove_children()

        healthy = sum(1 for p in self.monitor.processes if p.status == "idle")
        running = sum(1 for p in self.monitor.processes if p.status == "running")
        errors = sum(1 for p in self.monitor.processes if p.status == "error")
        pending = sum(1 for p in self.monitor.processes if p.status == "pending")

        stats_text = f"✓ {healthy} Healthy | ⚡ {running} Running | ❌ {errors} Errors | ⊙ {pending} Pending"
        container.mount(Label(stats_text, classes="stat-line"))

    def _update_ollama_table(self) -> None:
        """Update Ollama DataTable."""
        table = self.query_one("#ollama-table", OllamaTable)
        table.clear()

        for model in self.monitor.ollama_models:
            size_str = f"{model.size_mb / 1024:.1f} GB" if model.size_mb > 1024 else f"{model.size_mb:.0f} MB"
            status = "LOADED 🔥" if model.loaded else "idle 💤"

            table.add_row(
                model.name,
                size_str,
                status,
                "✓" if model.loaded else "○",
            )

    def _update_ollama_stats(self) -> None:
        """Update Ollama summary stats."""
        container = self.query_one("#ollama-stats", Container)
        container.remove_children()

        total_size = sum(m.size_mb for m in self.monitor.ollama_models)
        loaded_size = sum(m.size_mb for m in self.monitor.ollama_models if m.loaded)

        stats_lines = []
        if self.monitor.ollama_models:
            stats_lines.append(f"Total Available: {total_size / 1024:.1f} GB")
            stats_lines.append(f"VRAM Loaded: {loaded_size / 1024:.1f} GB")
        else:
            stats_lines.append("No Ollama models installed")

        for line in stats_lines:
            container.mount(Label(line, classes="stat-line"))

    def _update_claude_table(self) -> None:
        """Update Claude sessions DataTable."""
        table = self.query_one("#claude-table", ClaudeTable)
        table.clear()

        for session in self.monitor.claude_sessions:
            ago = datetime.now() - session.last_modified
            ago_str = self.monitor._format_timedelta(ago) + " ago"

            size_str = f"{session.size_mb / 1024:.1f} MB" if session.size_mb > 1 else f"{session.size_mb * 1024:.0f} KB"

            activity = self._get_activity_emoji(ago)

            table.add_row(
                session.name,
                size_str,
                ago_str,
                f"{session.token_estimate:,}",
                activity,
            )

    def _update_claude_stats(self) -> None:
        """Update Claude summary stats."""
        container = self.query_one("#claude-stats", Container)
        container.remove_children()

        total_sessions = len(self.monitor.claude_sessions)
        total_size = sum(s.size_mb for s in self.monitor.claude_sessions)
        total_tokens = sum(s.token_estimate for s in self.monitor.claude_sessions)

        stats_text = f"Sessions: {total_sessions} | Total Size: {total_size:.1f} MB | Est. Tokens: {total_tokens:,}"
        container.mount(Label(stats_text, classes="stat-line"))

    def _update_status_bar(self) -> None:
        """Update status bar."""
        status = self.query_one("#status-bar", Static)
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status.update(f"Last update: {time_str} | Updates: {self.update_counter} | [r] Refresh | [?] Help | [q] Quit")

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for process status."""
        emoji_map = {
            "running": "⚡",
            "idle": "✓",
            "error": "❌",
            "pending": "⊙",
        }
        return emoji_map.get(status, "○")

    def _get_activity_emoji(self, ago: timedelta) -> str:
        """Get emoji for Claude session activity level."""
        if ago < timedelta(minutes=5):
            return "🔥 Hot"
        elif ago < timedelta(hours=1):
            return "🟡 Warm"
        else:
            return "💤 Idle"

    def action_refresh(self) -> None:
        """Force immediate refresh."""
        asyncio.create_task(self._update_all_data())

    def action_toggle_logs(self) -> None:
        """Toggle logs view (placeholder)."""
        self.notify("📋 Logs feature coming soon", timeout=3)

    def action_show_help(self) -> None:
        """Show help modal."""
        help_text = """
        Process Monitor Dashboard - Keyboard Shortcuts

        [r]  - Force refresh all data
        [l]  - Toggle logs view
        [?]  - Show this help
        [q]  - Quit the dashboard

        Mouse Support:
        - Click to select tables
        - Scroll to see more rows
        - Click tabs to switch sections

        Layout:
        - Processes: Background task status and schedules
        - Ollama: Local LLM models and memory usage
        - Claude: Active session memory and token estimates

        Data refreshes automatically every 5 seconds.
        """
        self.notify(help_text, title="Help", timeout=10)


def main():
    """Launch the dashboard."""
    app = ProcessMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
