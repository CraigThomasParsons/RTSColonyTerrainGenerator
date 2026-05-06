"""Advanced log monitoring with state tracking and semantic awareness."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

LOG_LINE_PATTERN = re.compile(
    r"^(?P<ts>\S+) \[job=(?P<job>[^\]]+)\] \[stage=(?P<stage>[^\]]+)\] (?P<level>\S+) (?P<msg>.*)$"
)


@dataclass
class LogEntry:
    """Parsed log line with metadata."""

    timestamp: str
    job_id: str
    stage: str
    level: str
    message: str
    raw: str


@dataclass
class StageState:
    """Track state for a single stage."""

    name: str
    first_seen: float = 0.0
    last_seen: float = 0.0
    line_count: int = 0
    errors: int = 0
    warnings: int = 0
    completed: bool = False


@dataclass
class SentinelState:
    """Aggregate monitoring state across the pipeline."""

    job_id: str = "unknown"
    start_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    stages: Dict[str, StageState] = field(default_factory=dict)
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0
    issues: Dict[str, int] = field(default_factory=dict)
    recent_lines: List[str] = field(default_factory=list)
    seen_job_ids: Set[str] = field(default_factory=set)

    def elapsed_seconds(self) -> float:
        """Time since monitoring started."""
        return time.time() - self.start_time

    def idle_seconds(self) -> float:
        """Time since last log activity."""
        return time.time() - self.last_activity

    def get_or_create_stage(self, stage_name: str) -> StageState:
        """Get or create stage state."""
        if stage_name not in self.stages:
            self.stages[stage_name] = StageState(name=stage_name, first_seen=time.time())
        return self.stages[stage_name]


class LogSentinel:
    """Advanced log monitoring with semantic flow analysis."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.state = SentinelState()
        self._file_handle: Optional[object] = None
        self._position = 0

    def start(self) -> None:
        """Begin monitoring the log file."""
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_path}")

        self._file_handle = self.log_path.open("r", encoding="utf-8", errors="replace")
        self._file_handle.seek(0, os.SEEK_END)
        self._position = self._file_handle.tell()

    def stop(self) -> None:
        """Stop monitoring and close file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def poll(self) -> List[LogEntry]:
        """Read new log lines since last poll."""
        if not self._file_handle:
            return []

        entries = []
        while True:
            line = self._file_handle.readline()
            if not line:
                break

            line = line.rstrip("\n")
            if not line:
                continue

            entry = self._parse_line(line)
            if entry:
                self._update_state(entry)
                entries.append(entry)
            else:
                # Track unparsed lines as recent activity
                self.state.recent_lines.append(line)
                if len(self.state.recent_lines) > 50:
                    self.state.recent_lines.pop(0)

        return entries

    def _parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a log line into structured entry."""
        match = LOG_LINE_PATTERN.match(line)
        if not match:
            return None

        groups = match.groupdict()
        return LogEntry(
            timestamp=groups["ts"],
            job_id=groups["job"],
            stage=groups["stage"],
            level=groups["level"].upper(),
            message=groups["msg"],
            raw=line,
        )

    def _update_state(self, entry: LogEntry) -> None:
        """Update sentinel state with new log entry."""
        now = time.time()
        self.state.last_activity = now

        # Track job IDs
        if entry.job_id != "unknown":
            self.state.seen_job_ids.add(entry.job_id)
            if self.state.job_id == "unknown":
                self.state.job_id = entry.job_id

        # Update stage state
        stage = self.state.get_or_create_stage(entry.stage)
        stage.last_seen = now
        stage.line_count += 1

        # Count by level
        if entry.level == "ERROR":
            self.state.total_errors += 1
            stage.errors += 1
        elif entry.level == "WARN":
            self.state.total_warnings += 1
            stage.warnings += 1
        else:
            self.state.total_info += 1

        # Detect semantic issues
        self._detect_issues(entry)

        # Keep recent lines
        self.state.recent_lines.append(entry.raw)
        if len(self.state.recent_lines) > 50:
            self.state.recent_lines.pop(0)

    def _detect_issues(self, entry: LogEntry) -> None:
        """Detect known failure patterns and record issues."""
        patterns = {
            "Failed to parse maptiles": "Maptiles parse failed → verify Tiler binary output",
            "Failed to parse weather": "Weather parse failed → verify WeatherAnalyses binary format",
            "Tile count mismatch": "Tile count mismatch → check cell vs tile resolution (2x)",
            "Class.*not found": "PHP autoload error → verify PSR-4 filename",
            "Invalid numeric literal": "Non-JSON log line parsed → confirm log format",
            "No .* found in": "Missing upstream artifact → check dependency completion",
            "Timeout": "Stage timeout → verify systemd service and worker health",
        }

        for pattern, issue_desc in patterns.items():
            if re.search(pattern, entry.message, re.IGNORECASE):
                self.state.issues[issue_desc] = self.state.issues.get(issue_desc, 0) + 1

    def compute_health_score(self, stale_threshold: int = 15) -> int:
        """Compute health score based on activity and errors.

        Score starts at 100 and is penalized for:
        - Errors (−15 each)
        - Warnings (−5 each)
        - Stale logs (−20 if idle > threshold)
        - Known issues (−3 per occurrence)
        """
        score = 100

        score -= self.state.total_errors * 15
        score -= self.state.total_warnings * 5

        if self.state.idle_seconds() > stale_threshold:
            score -= 20

        issue_penalty = sum(self.state.issues.values()) * 3
        score -= issue_penalty

        return max(0, score)

    def detect_stalled_stages(self, stage_timeouts: Dict[str, int]) -> List[str]:
        """Identify stages that appear stalled beyond their timeout."""
        stalled = []
        now = time.time()

        for stage_name, stage_state in self.state.stages.items():
            timeout = stage_timeouts.get(stage_name, 120)
            if stage_state.last_seen > 0 and not stage_state.completed:
                idle = now - stage_state.last_seen
                if idle > timeout:
                    stalled.append(f"{stage_name} (idle {int(idle)}s > {timeout}s)")

        return stalled
