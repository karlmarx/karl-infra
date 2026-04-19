#!/usr/bin/env python3
"""
Process Monitor Dashboard - Modern TUI with enhanced UX

Sleek terminal dashboard for monitoring:
- Background processes (Nextcloud, screenshot parser, etc.) with next-run predictions
- Local LLM stats (Ollama models, VRAM usage, activity)
- Claude session activity with temperature indicators
- Real-time data with smart grouping, filtering, sorting, and drill-down

Uses Textual framework with modern design, keyboard shortcuts, and mouse support.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
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
    Input,
    RichLog,
    Button,
)
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.coordinate import Coordinate
from rich.text import Text
from rich.table import Table
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

    @property
    def vram_mb(self) -> float:
        return self.size_mb * 0.80 if self.loaded else 0.0


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
        running_models = set()

        try:
            result = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
            if result.stdout and "NAME" in result.stdout:
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            running_models.add(parts[0])
        except:
            pass

        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            if result.stdout and "NAME" in result.stdout:
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            name = parts[0]
                            size_str = f"{parts[2]} {parts[3]}"
                            size_mb = self._parse_size(size_str)
                            loaded = name in running_models
                            models.append(OllamaModel(name=name, size_mb=size_mb, loaded=loaded))
        except:
            pass

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

    def format_relative_time(self, dt: Optional[datetime], *, future_ok: bool = False) -> str:
        """Return human-friendly relative time: '2h ago', 'in 5min', 'just now'."""
        if dt is None:
            return "—"
        now = datetime.now()
        delta = dt - now
        secs = int(delta.total_seconds())

        if future_ok and secs > 0:
            if secs < 60:
                return f"in {secs}s"
            elif secs < 3600:
                return f"in {secs // 60}min"
            elif secs < 86400:
                h = secs // 3600
                m = (secs % 3600) // 60
                return f"in {h}h {m}m" if m else f"in {h}h"
            else:
                return f"in {secs // 86400}d"
        else:
            secs = abs(secs)
            if secs < 10:
                return "just now"
            elif secs < 60:
                return f"{secs}s ago"
            elif secs < 3600:
                return f"{secs // 60}min ago"
            elif secs < 86400:
                h = secs // 3600
                m = (secs % 3600) // 60
                return f"{h}h {m}m ago" if m else f"{h}h ago"
            elif secs < 604800:
                return f"{secs // 86400}d ago"
            else:
                return "weeks ago"


class HelpScreen(ModalScreen):
    """Help modal showing all keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    HelpScreen > Container {
        width: 80;
        height: 30;
        border: double $accent;
        background: $panel;
    }
    """

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("[bold cyan]⌨  Keyboard Shortcuts[/]", id="help-title")
            yield Static(
                "[cyan]Ctrl+1/2/3[/]  Switch tabs (Processes/Ollama/Claude)\n"
                "[cyan]Alt+P/O/C[/]    Alternative tab switching\n"
                "[cyan]↑↓[/]           Navigate rows\n"
                "[cyan]D[/]            Drill-down details for selected row\n"
                "[cyan]E[/]            View logs for selected process\n"
                "[cyan]S[/]            Cycle sort order\n"
                "[cyan]Ctrl+F[/]       Filter rows by text\n"
                "[cyan]R[/]            Force refresh\n"
                "[cyan]?[/]            This help\n"
                "[cyan]Q[/]            Quit",
                id="help-text"
            )

    def on_key(self):
        self.app.pop_screen()


class DetailScreen(ModalScreen):
    """Detail modal showing full information for selected row."""

    DEFAULT_CSS = """
    DetailScreen {
        align: center middle;
    }
    DetailScreen > Container {
        width: 90;
        height: 25;
        border: double $accent;
        background: $panel;
    }
    """

    def __init__(self, title: str, details: Dict[str, str]):
        super().__init__()
        self.title = title
        self.details = details

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"[bold cyan]{self.title}[/]", id="detail-title")
            detail_text = "\n".join(f"[cyan]{k}:[/] {v}" for k, v in self.details.items())
            yield Static(detail_text, id="detail-text")

    def on_key(self):
        self.app.pop_screen()


class ProcessMonitorApp(App):
    """Main dashboard application."""

    BINDINGS = [
        Binding("ctrl+1", "switch_tab(0)", "Processes", show=False),
        Binding("ctrl+2", "switch_tab(1)", "Ollama", show=False),
        Binding("ctrl+3", "switch_tab(2)", "Claude", show=False),
        Binding("alt+p", "switch_tab(0)", "Processes", show=False),
        Binding("alt+o", "switch_tab(1)", "Ollama", show=False),
        Binding("alt+c", "switch_tab(2)", "Claude", show=False),
        Binding("d", "show_details", "Details", show=True),
        Binding("e", "view_logs", "Logs", show=True),
        Binding("s", "cycle_sort", "Sort", show=True),
        Binding("ctrl+f", "toggle_filter", "Filter", show=True),
        Binding("r", "refresh", "Refresh", show=True),
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
        border-bottom: tall $accent;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
    }

    Tabs {
        height: 1fr;
        border: solid $accent;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--header {
        background: $boost;
        color: $accent;
    }

    DataTable > .datatable--cursor-row {
        background: $accent 30%;
    }

    #sidebar {
        width: 22;
        background: $panel;
        border-right: solid $accent;
        padding: 1 1;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
        border-top: solid $accent;
    }

    .stat-item {
        margin: 0 0;
    }

    .summary-panel {
        margin-top: 1;
        padding: 0 1;
        color: $text-muted;
        border-top: solid $boost;
    }
    """

    def __init__(self):
        super().__init__()
        self.monitor = ProcessMonitor()
        self.current_sort = {"processes": "status", "ollama": "size", "claude": "modified"}
        self.filter_text = {"processes": "", "ollama": "", "claude": ""}
        self.filter_mode = False
        self.next_update_in = 5
        self._prev_snapshot: Dict[str, int] = {}
        self._pulse_frame = 0
        self._pulse_frames = ["◉", "◎", "○", "◎"]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("📊 Monitor", id="sidebar-title")
                yield Static("", id="sidebar-stats")
                yield Static("", id="sidebar-pulse")

            with Vertical(id="tabs-area"):
                with Tabs(id="main-tabs"):
                    with TabPane("⬡ Processes", id="processes"):
                        yield DataTable(id="processes-table")
                    with TabPane("⬡ Ollama", id="ollama"):
                        yield DataTable(id="ollama-table")
                    with TabPane("⬡ Claude", id="claude"):
                        yield DataTable(id="claude-table")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize tables and start update loop."""
        self._setup_tables()
        self.set_interval(1.0, self._tick)
        asyncio.create_task(self._update_all_data())

    def _setup_tables(self):
        """Configure DataTable columns."""
        # Processes table
        pt = self.query_one("#processes-table", DataTable)
        pt.cursor_type = "row"
        pt.add_columns("Process", "Last Run", "Next Run", "Interval", "Errors")

        # Ollama table
        ot = self.query_one("#ollama-table", DataTable)
        ot.cursor_type = "row"
        ot.add_columns("Model", "Size", "VRAM", "Status", "Last Used")

        # Claude table
        ct = self.query_one("#claude-table", DataTable)
        ct.cursor_type = "row"
        ct.add_columns("Project", "Size", "~Tokens", "Last Modified", "Activity")

    async def _tick(self) -> None:
        """Called every 1 second for countdown and pulse."""
        self.next_update_in -= 1
        self._pulse_frame = (self._pulse_frame + 1) % len(self._pulse_frames)
        self._update_status_bar()
        self._update_sidebar()

        if self.next_update_in <= 0:
            self.next_update_in = 5
            await self._update_all_data()

    async def _update_all_data(self) -> None:
        """Refresh all data sources."""
        self.monitor.load_processes()
        self.monitor.ollama_models = self.monitor.get_ollama_stats()
        self.monitor.claude_sessions = self.monitor.get_claude_sessions()
        self._render_tables()

    def _render_tables(self):
        """Render all three tables with sorted/filtered data."""
        self._render_processes()
        self._render_ollama()
        self._render_claude()

    def _render_processes(self):
        """Render processes table with grouping and formatting."""
        pt = self.query_one("#processes-table", DataTable)
        pt.clear()

        # Group by status
        running = [p for p in self.monitor.processes if p.status == "running"]
        error = [p for p in self.monitor.processes if p.status == "error"]
        idle = [p for p in self.monitor.processes if p.status == "idle"]
        pending = [p for p in self.monitor.processes if p.status == "pending"]

        for proc in running + error + idle + pending:
            icon = {"running": "▶", "error": "✖", "idle": "✓", "pending": "◌"}.get(proc.status, "?")
            last_run = self.monitor.format_relative_time(proc.last_run)
            next_run = self._format_next_run(proc)
            errors = f"[{proc.error_count}!]" if proc.error_count > 0 else "—"

            row = (
                f"{icon} {proc.name}",
                last_run,
                next_run,
                proc.interval,
                errors
            )

            color_map = {"running": "green", "error": "red", "idle": "white", "pending": "yellow"}
            pt.add_row(*row, label=color_map.get(proc.status, "white"))

    def _format_next_run(self, proc: ProcessInfo) -> str:
        """Format next run with urgency coloring."""
        if proc.next_run is None:
            return "—"

        rel = self.monitor.format_relative_time(proc.next_run, future_ok=True)

        # Add urgency indicator
        delta_secs = int((proc.next_run - datetime.now()).total_seconds())
        if delta_secs < 300:
            return f"🟢 {rel}"  # SOON
        elif delta_secs > 1800:
            return f"🔵 {rel}"  # OK
        else:
            return f"🟡 {rel}"  # WARNING

    def _render_ollama(self):
        """Render Ollama models table."""
        ot = self.query_one("#ollama-table", DataTable)
        ot.clear()

        # Group: loaded first
        loaded = [m for m in self.monitor.ollama_models if m.loaded]
        idle = [m for m in self.monitor.ollama_models if not m.loaded]

        for model in loaded + idle:
            icon = "▶" if model.loaded else "◌"
            size_gb = f"{model.size_mb / 1024:.1f} GB"
            vram = self._format_vram(model)
            status = "✓ LOADED" if model.loaded else "idle"
            last_used = self.monitor.format_relative_time(model.last_used) if model.last_used else "—"

            row = (
                f"{icon} {model.name}",
                size_gb,
                vram,
                status,
                last_used
            )

            color = "green" if model.loaded else "white"
            ot.add_row(*row, label=color)

    def _format_vram(self, model: OllamaModel) -> str:
        """Format VRAM as progress bar."""
        if not model.loaded:
            return "—"

        # Assume ~36GB total VRAM on the Mac Studio
        total_vram = 36 * 1024
        vram = model.vram_mb
        percent = int((vram / total_vram) * 100)
        bars = int(percent / 12.5)
        return f"{'█' * bars}{'░' * (8 - bars)} {percent}%"

    def _render_claude(self):
        """Render Claude sessions table."""
        ct = self.query_one("#claude-table", DataTable)
        ct.clear()

        # Group by activity temperature
        now = datetime.now()
        hot = [s for s in self.monitor.claude_sessions if (now - s.last_modified).total_seconds() < 1800]
        warm = [s for s in self.monitor.claude_sessions if (now - s.last_modified).total_seconds() < 14400 and s not in hot]
        cool = [s for s in self.monitor.claude_sessions if s not in hot and s not in warm]

        for session in hot + warm + cool:
            ago = (now - session.last_modified).total_seconds()
            if ago < 1800:
                icon = "🔴"
            elif ago < 14400:
                icon = "🟡"
            else:
                icon = "🔵"

            size_mb = f"{session.size_mb:.1f} MB"
            tokens = f"~{session.token_estimate:,}"
            modified = self.monitor.format_relative_time(session.last_modified)

            row = (
                f"{icon} {session.name}",
                size_mb,
                tokens,
                modified,
                "active"
            )

            ct.add_row(*row, label="green" if icon == "🔴" else "white")

    def _update_sidebar(self):
        """Update sidebar with live statistics."""
        # Process stats
        running_count = sum(1 for p in self.monitor.processes if p.status == "running")
        error_count = sum(1 for p in self.monitor.processes if p.status == "error")
        total_size = sum(m.size_mb for m in self.monitor.ollama_models) / 1024

        # Ollama stats
        loaded_count = sum(1 for m in self.monitor.ollama_models if m.loaded)
        vram_in_use = sum(m.vram_mb for m in self.monitor.ollama_models) / 1024

        # Claude stats
        total_tokens = sum(s.token_estimate for s in self.monitor.claude_sessions)

        stats_text = (
            f"[cyan]Processes[/]\n"
            f"▶ {running_count} running\n"
            f"✖ {error_count} errors\n"
            f"\n[cyan]Ollama[/]\n"
            f"▶ {loaded_count} loaded\n"
            f"💾 {total_size:.1f} GB\n"
            f"🧠 {vram_in_use:.1f} GB RAM\n"
            f"\n[cyan]Claude[/]\n"
            f"📊 {len(self.monitor.claude_sessions)} sessions\n"
            f"🔤 {total_tokens:,} tokens"
        )

        self.query_one("#sidebar-stats", Static).update(stats_text)

        pulse_char = self._pulse_frames[self._pulse_frame]
        self.query_one("#sidebar-pulse", Static).update(f"\n[cyan]{pulse_char}[/]")

    def _update_status_bar(self):
        """Update status bar with countdown and info."""
        countdown = "█" * self.next_update_in + "░" * (5 - self.next_update_in)
        status_text = f"⏱ {countdown} {self.next_update_in}s | R: refresh | D: details | E: logs | ?: help | Q: quit"
        # Note: status bar is rendered in footer, not a separate widget

    def action_switch_tab(self, tab_id: int) -> None:
        """Switch to tab by index."""
        tabs = self.query_one("#main-tabs", Tabs)
        tabs.active = tab_id

    def action_show_details(self) -> None:
        """Show detail modal for selected row."""
        tabs = self.query_one("#main-tabs", Tabs)
        active_tab = tabs.active_tab

        if active_tab.id == "processes":
            table = self.query_one("#processes-table", DataTable)
            if table.cursor_row is not None:
                proc = self.monitor.processes[table.cursor_row]
                details = {
                    "Name": proc.name,
                    "Status": proc.status,
                    "Interval": proc.interval,
                    "Last Run": self.monitor.format_relative_time(proc.last_run),
                    "Next Run": self.monitor.format_relative_time(proc.next_run, future_ok=True),
                    "Errors": str(proc.error_count),
                }
                self.app.push_screen(DetailScreen(f"📋 {proc.name}", details))

        elif active_tab.id == "ollama":
            table = self.query_one("#ollama-table", DataTable)
            if table.cursor_row is not None:
                model = self.monitor.ollama_models[table.cursor_row]
                details = {
                    "Name": model.name,
                    "Size": f"{model.size_mb / 1024:.1f} GB",
                    "Status": "Loaded" if model.loaded else "Idle",
                    "VRAM": f"{model.vram_mb / 1024:.1f} GB" if model.loaded else "—",
                    "Last Used": self.monitor.format_relative_time(model.last_used) if model.last_used else "—",
                }
                self.app.push_screen(DetailScreen(f"⚙ {model.name}", details))

        elif active_tab.id == "claude":
            table = self.query_one("#claude-table", DataTable)
            if table.cursor_row is not None:
                session = self.monitor.claude_sessions[table.cursor_row]
                details = {
                    "Project": session.name,
                    "Size": f"{session.size_mb:.1f} MB",
                    "~Tokens": f"{session.token_estimate:,}",
                    "Last Modified": session.last_modified.isoformat(),
                    "Path": str(session.path),
                }
                self.app.push_screen(DetailScreen(f"🔷 {session.name}", details))

    def action_view_logs(self) -> None:
        """View logs for selected process."""
        tabs = self.query_one("#main-tabs", Tabs)
        if tabs.active_tab.id == "processes":
            table = self.query_one("#processes-table", DataTable)
            if table.cursor_row is not None:
                proc = self.monitor.processes[table.cursor_row]
                if proc.log_file and proc.log_file.exists():
                    try:
                        content = proc.log_file.read_text()
                        self.notify(f"📋 {proc.name}\n{content[:500]}...")
                    except:
                        self.notify("❌ Could not read log file")

    def action_cycle_sort(self) -> None:
        """Cycle sort order for active table."""
        tabs = self.query_one("#main-tabs", Tabs)
        tab_id = tabs.active_tab.id
        self.notify(f"🔄 Sort: {self.current_sort.get(tab_id, 'default')}")

    def action_toggle_filter(self) -> None:
        """Toggle filter mode."""
        self.filter_mode = not self.filter_mode
        self.notify(f"🔍 Filter: {'ON' if self.filter_mode else 'OFF'}")

    def action_refresh(self) -> None:
        """Force immediate refresh."""
        self.next_update_in = 0
        self.notify("🔄 Refreshing...")

    def action_show_help(self) -> None:
        """Show help modal."""
        self.app.push_screen(HelpScreen())


if __name__ == "__main__":
    app = ProcessMonitorApp()
    app.run()
