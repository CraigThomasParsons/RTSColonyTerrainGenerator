"""
Real-time file tailing for log monitoring.

This module provides classes for watching log files and streaming new
entries as they're written. It's designed for the TUI to display live
log output from running pipeline stages.

Purpose:
    Pipeline stages write log entries to JSONL files as they process.
    The TailManager and FileTail classes monitor these files and emit
    structured LogEntry objects as new lines are appended.

Design Decisions:
    - Uses polling rather than inotify for cross-platform simplicity
    - Handles file truncation/rotation gracefully
    - Buffers partial lines to handle incomplete writes
    - Discovers new log files dynamically
    - Supports both JSONL (stage logs) and plain text (mapgenctl.log)
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List
from queue import Queue

from .model import LogEntry


class FileTail:
    """
    Tail a single log file and emit LogEntry objects for new lines.

    Tracks the file offset and polls for new content. Handles common
    edge cases like file truncation, partial lines, and encoding errors.

    Attributes:
        path: Path to the log file being tailed.
        job_id: Job ID to associate with emitted entries.
        stage: Stage name to associate with emitted entries.
        offset: Current read position in the file.
        partial: Incomplete line buffer (line without trailing newline).
        seq: Sequence counter for stable entry ordering.

    Example:
        >>> tail = FileTail(Path("logs/heightmap.log.jsonl"), "abc-123", "heightmap")
        >>> entries = tail.poll()  # Returns new entries since last poll
    """

    def __init__(self, path: Path, job_id: str, stage: str):
        """
        Initialize a file tail for a specific log file.

        Args:
            path: Path to the JSONL log file to tail.
            job_id: Job ID to tag emitted entries with.
            stage: Pipeline stage name for entries (may be overridden
                   by the entry's own stage field if present).
        """
        self.path = path
        self.job_id = job_id
        self.stage = stage
        # Track where we left off reading in the file
        self.offset = 0
        # Buffer for incomplete lines that don't end with newline yet
        self.partial = ""
        # Sequence number helps with stable sorting of near-simultaneous events
        self.seq = 0

    def _read_new_lines(self) -> List[str]:
        """Read new complete lines from the file since last poll."""
        # File might not exist yet if stage hasn't started
        if not self.path.exists():
            return []

        # Check current file size
        size = self.path.stat().st_size

        # Detect file truncation or replacement (logrotate, manual clear, etc.)
        if size < self.offset:
            # File was truncated - reset to beginning
            self.offset = 0
            self.partial = ""

        # No new content since last poll
        if size == self.offset:
            return []

        # Read new content from where we left off
        with self.path.open("rb") as f:
            f.seek(self.offset)
            data = f.read()
            self.offset = size

        # Decode bytes to string, replacing any invalid UTF-8 sequences
        text = data.decode("utf-8", errors="replace")

        # Prepend any buffered partial line from the last poll
        text = self.partial + text

        # Split into lines (may include incomplete final line)
        lines = text.splitlines(keepends=False)

        # If file doesn't end with newline, last line is incomplete
        # Buffer it for the next poll
        if not text.endswith("\n"):
            self.partial = lines.pop() if lines else ""
        else:
            self.partial = ""

        return lines

    def poll(self) -> List[LogEntry]:
        """
        Read new log entries from the file since the last poll.

        Checks for new content, parses complete JSON lines, and returns
        them as LogEntry objects. Handles file truncation and partial
        lines at the end of the file.

        Returns:
            List[LogEntry]: New log entries read from the file.
                           Empty list if no new content or file missing.
        """
        lines = self._read_new_lines()

        # Parse each complete line as JSON and emit LogEntry objects
        entries = []
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines - may be corrupted or non-JSON
                continue

            # Increment sequence for stable ordering of simultaneous events
            self.seq += 1

            # Build LogEntry, pulling fields from the JSON object
            # Fall back to constructor values if JSON doesn't have the field
            entries.append(LogEntry(
                job_id=self.job_id,
                stage=obj.get("stage", self.stage),  # Entry can override stage
                timestamp=obj.get("ts"),  # JSONL uses 'ts' field
                level=obj.get("level"),
                event=obj.get("event"),
                message=obj.get("msg"),  # JSONL uses 'msg' field
                raw=obj,  # Preserve full JSON for debugging
                arrival_time=time.monotonic(),  # For ordering entries without timestamps
                seq=self.seq,
            ))

        return entries


class PlainTextTail(FileTail):
    """
    Tail a plain text log file (mapgenctl.log format).

    Parses lines in the format:
        <timestamp> [job=<id>] [stage=<stage>] <LEVEL> <message>

    Example:
        2024-01-15T12:00:00Z [job=abc-123] [stage=heightmap] INFO Processing started
    """

    # Regex to parse mapgenctl log lines
    # Format: <timestamp> [job=<id>] [stage=<stage>] <LEVEL> <message>
    LINE_PATTERN = re.compile(
        r"^(?P<ts>\S+)\s+"
        r"\[job=(?P<job_id>[^\]]+)\]\s+"
        r"\[stage=(?P<stage>[^\]]+)\]\s+"
        r"(?P<level>\w+)\s+"
        r"(?P<msg>.*)$"
    )

    def poll(self) -> List[LogEntry]:
        """
        Read new log entries from the plain text file.

        Parses lines using the mapgenctl log format and returns
        LogEntry objects.

        Returns:
            List[LogEntry]: New log entries read from the file.
        """
        lines = self._read_new_lines()

        entries = []
        for line in lines:
            match = self.LINE_PATTERN.match(line)
            if not match:
                # Skip lines that don't match the expected format
                continue

            self.seq += 1

            entries.append(LogEntry(
                job_id=match.group("job_id"),
                stage=match.group("stage"),
                timestamp=match.group("ts"),
                level=match.group("level"),
                event=None,  # Plain text logs don't have structured events
                message=match.group("msg"),
                raw={"line": line},  # Preserve original line
                arrival_time=time.monotonic(),
                seq=self.seq,
            ))

        return entries


class TailManager:
    """
    Manage multiple file tails for a single job.

    Automatically discovers new log files as stages start and polls
    all known files. Entries are pushed to a queue for the UI to consume.

    Attributes:
        job_id: The job being monitored.
        out_queue: Queue to push log entries to.
        tails: Dict mapping stage names to FileTail instances.
        job_dir: Path to the job's log directory.

    Example:
        >>> queue = Queue()
        >>> manager = TailManager("abc-123", queue)
        >>> while True:
        ...     manager.tick()
        ...     # Process entries from queue
        ...     time.sleep(0.25)
    """

    def __init__(self, job_id: str, out_queue: Queue):
        """
        Initialize a tail manager for a specific job.

        Args:
            job_id: The job ID to monitor logs for.
            out_queue: Queue to push LogEntry objects to.
        """
        self.job_id = job_id
        self.out_queue = out_queue
        # Map from stage name to FileTail instance
        self.tails: Dict[str, FileTail] = {}

        # Directory where this job's logs are stored
        # Use MAPGEN_LOG_ROOT if set, otherwise fallback to ./logs
        log_root = os.environ.get("MAPGEN_LOG_ROOT", "./logs")
        self.job_dir = Path(log_root) / "jobs" / job_id

    def tick(self) -> None:
        """
        Poll for new log files and entries.

        Should be called periodically (e.g., every 250ms) in a background
        thread. Discovers new stage log files and polls all known tails.

        Side Effects:
            - May create new FileTail instances for newly discovered logs
            - Pushes LogEntry objects to the output queue
        """
        # Discover mapgenctl.log (plain text orchestration log)
        mapgenctl_log = self.job_dir / "mapgenctl.log"
        if mapgenctl_log.exists() and "mapgenctl" not in self.tails:
            self.tails["mapgenctl"] = PlainTextTail(
                mapgenctl_log, self.job_id, "mapgenctl"
            )

        # Discover JSONL stage logs (heightmap, tiler, weather, etc.)
        # This handles stages that start after we began monitoring
        if self.job_dir.exists():
            for path in self.job_dir.glob("*.log.jsonl"):
                # Extract stage name from filename (e.g., "heightmap.log.jsonl" -> "heightmap")
                stage = path.stem.replace(".log", "")
                # Only create a tail if we haven't seen this stage before
                if stage not in self.tails:
                    self.tails[stage] = FileTail(path, self.job_id, stage)

        # Poll all known tails for new entries
        for tail in self.tails.values():
            for entry in tail.poll():
                try:
                    # Non-blocking put - if queue is full, we drop entries
                    # This prevents blocking the tail thread on a slow UI
                    self.out_queue.put_nowait(entry)
                except:
                    # Queue full - silently drop entry to prevent blocking
                    pass

