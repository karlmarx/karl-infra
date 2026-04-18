#!/usr/bin/env python
"""
Enhanced Process Monitor Dashboard

Real-time terminal UI for monitoring:
- Background processes (Nextcloud, screenshot parser, etc.)
- Local LLM stats (Ollama models, VRAM usage, inference time)
- Claude session activity and memory usage

Pure Python with no external dependencies
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import re
import time
import os
import stat

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

class ANSI:
    """ANSI color and style constants."""
    # Colors
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Box drawing (work across most terminals)
    H_LINE = "─"
    V_LINE = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"
    T_CROSS = "┬"
    B_CROSS = "┴"
    L_CROSS = "├"
    R_CROSS = "┤"
    CROSS = "┼"

class ProcessMonitor:
    """Monitor and display background processes, LLM activity, and Claude sessions."""

    def __init__(self):
        self.processes: List[ProcessInfo] = []
        self.ollama_models: List[OllamaModel] = []
        self.claude_sessions: List[ClaudeSession] = []
        self.update_interval = 5  # seconds
        self.history: List[Tuple[datetime, int, int]] = []  # Track memory trend
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
                # Skip header line
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
                # Skip header line
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            name = parts[0]
                            # Parse size: size is in parts[2], unit is in parts[3]
                            # Format: "NAME ID SIZE UNIT MODIFIED..."
                            # e.g., "gemma4:latest c6eb396... 9.6 GB 2 days ago"
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
            # Handle various formats: "17 GB", "9.6GB", etc.
            size_str = size_str.strip()

            # Try to extract number and unit with regex
            import re as regex_module
            match = regex_module.search(r'([\d.]+)\s*(GB|MB|KB|B)', size_str, regex_module.IGNORECASE)
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

            # Fallback: try simple split
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

            # Get all project directories
            for item in projects_dir.iterdir():
                if not item.is_dir():
                    continue

                try:
                    # Get size
                    size_mb = self._get_dir_size(item) / (1024 * 1024)

                    # Get modification time
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)

                    # Only include recent sessions (last 7 days)
                    if mtime >= week_ago:
                        # Decode session name from path
                        display_name = item.name.replace("-Users-kmx-", "").replace("-", "/")
                        if len(display_name) > 30:
                            display_name = display_name[:27] + "..."

                        # Rough token estimate: ~400 tokens per MB
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

            # Sort by recent first
            sessions.sort(key=lambda s: s.last_modified, reverse=True)
            return sessions[:5]  # Return top 5 recent sessions
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

    def render_sparkline(self, values: List[float], width: int = 10) -> str:
        """Render simple ASCII sparkline from values."""
        if not values:
            return " " * width

        chars = "▁▂▃▄▅▆▇█"
        min_val = min(values)
        max_val = max(values)

        if min_val == max_val:
            return "█" * width

        result = ""
        for val in values[-width:]:
            idx = int((val - min_val) / (max_val - min_val) * (len(chars) - 1))
            result += chars[idx]

        return result

    def color_status(self, status: str, value: Optional[str] = None) -> str:
        """Return colored status string."""
        if status == "running":
            return f"{ANSI.RED}⚡ RUNNING{ANSI.RESET}"
        elif status == "error":
            return f"{ANSI.RED}❌ ERROR{ANSI.RESET}"
        elif status == "idle":
            return f"{ANSI.GREEN}✓ Idle{ANSI.RESET}"
        elif status == "pending":
            return f"{ANSI.GRAY}⊙ Pending{ANSI.RESET}"
        return status

    def render_box_section(self, title: str, lines: List[str], width: int = 50) -> List[str]:
        """Render a section with box drawing."""
        output = []

        # Title line
        title_display = f" {ANSI.BOLD}{title}{ANSI.RESET} "
        padding = width - len(title) - 2
        left_pad = padding // 2
        right_pad = padding - left_pad

        output.append(f"{ANSI.CYAN}{ANSI.TL}{ANSI.H_LINE * left_pad}{ANSI.RESET}{title_display}{ANSI.CYAN}{ANSI.H_LINE * right_pad}{ANSI.TR}{ANSI.RESET}")

        # Content lines
        for line in lines:
            # Strip ANSI codes for length calculation
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            padding = width - len(clean_line)
            output.append(f"{ANSI.CYAN}{ANSI.V_LINE}{ANSI.RESET}{line}{' ' * padding}{ANSI.CYAN}{ANSI.V_LINE}{ANSI.RESET}")

        # Bottom line
        output.append(f"{ANSI.CYAN}{ANSI.BL}{ANSI.H_LINE * width}{ANSI.BR}{ANSI.RESET}")

        return output

    def render_ascii(self):
        """Render dashboard as three-column layout."""
        os.system('clear' if os.name == 'posix' else 'cls')

        # Header
        print("\n" + "=" * 140)
        print(f"{ANSI.BOLD}PROCESS MONITOR DASHBOARD{ANSI.RESET}".center(140))
        print("=" * 140 + "\n")

        # Update all data
        for proc in self.processes:
            self.update_process_status(proc)

        self.ollama_models = self.get_ollama_stats()
        self.claude_sessions = self.get_claude_sessions()

        # Build three columns
        col1_lines = self._build_processes_column()
        col2_lines = self._build_ollama_column()
        col3_lines = self._build_claude_column()

        # Render columns side-by-side
        max_lines = max(len(col1_lines), len(col2_lines), len(col3_lines))

        for i in range(max_lines):
            line1 = col1_lines[i] if i < len(col1_lines) else ""
            line2 = col2_lines[i] if i < len(col2_lines) else ""
            line3 = col3_lines[i] if i < len(col3_lines) else ""

            # Pad lines to consistent width
            line1_clean = re.sub(r'\033\[[0-9;]*m', '', line1)
            line2_clean = re.sub(r'\033\[[0-9;]*m', '', line2)

            print(f"{line1:<46} {line2:<46} {line3}")

        # Footer
        print("\n" + "=" * 140)
        print(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refresh: {self.update_interval}s")
        print("\nKeys: [r] refresh  [l] logs  [e] errors  [q] quit")
        print("=" * 140 + "\n")

    def _build_processes_column(self) -> List[str]:
        """Build PROCESSES column."""
        lines = []
        lines.append(f"{ANSI.BOLD}{ANSI.CYAN}PROCESSES{ANSI.RESET}")
        lines.append("")

        for proc in self.processes:
            status_str = self.color_status(proc.status)

            if proc.status == "running":
                indicator = f"{ANSI.RED}🔥{ANSI.RESET}"
            elif proc.status == "error":
                indicator = f"{ANSI.RED}❌{ANSI.RESET}"
            else:
                indicator = f"{ANSI.GREEN}✓{ANSI.RESET}"

            # Short name
            short_name = proc.name.split()[0:2]
            display_name = " ".join(short_name)[:14]

            lines.append(f"{indicator} {display_name:<14} {status_str}")

            if proc.last_run:
                ago = datetime.now() - proc.last_run
                ago_str = self._format_timedelta(ago)
                lines.append(f"   {ANSI.GRAY}↻ {ago_str} ago{ANSI.RESET}")

        errors = sum(1 for p in self.processes if p.status == "error")
        running = sum(1 for p in self.processes if p.status == "running")

        lines.append("")
        lines.append(f"{ANSI.GREEN}✓ Healthy{ANSI.RESET}  {ANSI.YELLOW}⚠ Running: {running}{ANSI.RESET}")
        if errors > 0:
            lines.append(f"{ANSI.RED}❌ Errors: {errors}{ANSI.RESET}")

        return lines

    def _build_ollama_column(self) -> List[str]:
        """Build LOCAL LLM column."""
        lines = []
        lines.append(f"{ANSI.BOLD}{ANSI.BLUE}LOCAL LLM (Ollama){ANSI.RESET}")
        lines.append("")

        if not self.ollama_models:
            lines.append(f"{ANSI.GRAY}No models available{ANSI.RESET}")
        else:
            for model in self.ollama_models[:4]:  # Show top 4
                if model.loaded:
                    indicator = f"{ANSI.YELLOW}🔥{ANSI.RESET}"
                    status = f"{ANSI.YELLOW}LOADED{ANSI.RESET}"
                else:
                    indicator = f"{ANSI.GRAY}💤{ANSI.RESET}"
                    status = f"{ANSI.GRAY}idle{ANSI.RESET}"

                # Format size
                if model.size_mb > 1024:
                    size_str = f"{model.size_mb / 1024:.1f} GB"
                else:
                    size_str = f"{model.size_mb:.0f} MB"

                # Short name
                short_name = model.name.split(":")[0][:10]

                lines.append(f"{indicator} {short_name:<10} {size_str:>7}")
                lines.append(f"   {status}")

        # Memory summary
        total_size = sum(m.size_mb for m in self.ollama_models)
        loaded_size = sum(m.size_mb for m in self.ollama_models if m.loaded)

        lines.append("")
        if loaded_size > 0:
            lines.append(f"VRAM: {loaded_size/1024:.1f} GB loaded")
        if total_size > 0:
            lines.append(f"Available: {total_size/1024:.1f} GB")
        else:
            lines.append(f"{ANSI.GRAY}No models installed{ANSI.RESET}")

        return lines

    def _build_claude_column(self) -> List[str]:
        """Build CLAUDE SESSIONS column."""
        lines = []
        lines.append(f"{ANSI.BOLD}{ANSI.CYAN}CLAUDE SESSIONS{ANSI.RESET}")
        lines.append("")

        if not self.claude_sessions:
            lines.append(f"{ANSI.GRAY}No recent sessions{ANSI.RESET}")
        else:
            for session in self.claude_sessions[:5]:
                # Determine activity level
                ago = datetime.now() - session.last_modified
                if ago < timedelta(minutes=5):
                    activity = f"{ANSI.RED}🔥{ANSI.RESET}"
                elif ago < timedelta(hours=1):
                    activity = f"{ANSI.YELLOW}🟡{ANSI.RESET}"
                else:
                    activity = f"{ANSI.GRAY}💤{ANSI.RESET}"

                # Short name
                display_name = session.name[:18]

                lines.append(f"{activity} {display_name:<18}")

                # Size and time
                ago_str = self._format_timedelta(ago)
                if session.size_mb < 1:
                    size_str = f"{session.size_mb*1024:.0f} KB"
                else:
                    size_str = f"{session.size_mb:.1f} MB"

                lines.append(f"   {size_str:>6}  {ANSI.GRAY}{ago_str} ago{ANSI.RESET}")

        return lines

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

    def run(self):
        """Run the dashboard in loop."""
        try:
            while True:
                self.render_ascii()
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            print("\n[✓] Dashboard stopped\n")

def main():
    """Launch the dashboard."""
    monitor = ProcessMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
