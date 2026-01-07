"""
Job logging utilities for pipeline observability.

This module provides a structured logging system for tracking jobs as they
flow through the MapGenerator pipeline. Each job gets its own log file,
making it easy to debug issues and understand what happened during processing.

Purpose:
    When a job moves through multiple pipeline stages (Heightmap -> Tiler ->
    Weather -> TreePlanter), developers need a way to see the complete history
    of what happened. This module creates a single, append-only log file per
    job that all pipeline components write to.

Design Decisions:
    - One log file per job (not per stage) for easier correlation
    - Append-only writes to prevent data loss
    - Human-readable format with timestamps and structured fields
    - UTC timestamps for consistency across timezones
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path


def log_root() -> Path:
    """
    Return the root directory for all MapGenerator logs.

    Uses the MAPGEN_LOG_ROOT environment variable if set, otherwise
    falls back to the repository's logs/ directory.

    Returns:
        Path: Absolute path to the log root directory.

    Example:
        >>> os.environ["MAPGEN_LOG_ROOT"] = "/var/log/mapgen"
        >>> log_root()
        PosixPath('/var/log/mapgen')
    """
    root = os.environ.get("MAPGEN_LOG_ROOT")
    if root:
        return Path(root)
    # Fallback: <repo>/logs (joblog.py -> utils/ -> mapgenctl/ -> tools/ -> repo)
    return Path(__file__).resolve().parents[3] / "logs"


def job_log_dir(job_id: str) -> Path:
    """
    Return the log directory for a specific job.

    Each job gets its own directory under logs/jobs/ to store logs
    from all pipeline stages (mapgenctl, heightmap, tiler, etc.).

    Args:
        job_id: The unique identifier for the job.

    Returns:
        Path: Absolute path to the job's log directory.

    Example:
        >>> job_log_dir("abc-123-def")
        PosixPath('/home/user/.../logs/jobs/abc-123-def')
    """
    return log_root() / "jobs" / job_id


def job_log_path(job_id: str) -> Path:
    """
    Resolve the mapgenctl log file path for a specific job.

    The mapgenctl log is a plain text file containing orchestration logs.
    Stage-specific logs (heightmap, tiler, etc.) are JSONL files in the
    same directory.

    Args:
        job_id: The unique identifier for the job (typically a UUID string).

    Returns:
        Path: Absolute path to the job's mapgenctl log file.

    Example:
        >>> job_log_path("abc-123-def")
        PosixPath('/home/user/.../logs/jobs/abc-123-def/mapgenctl.log')
    """
    return job_log_dir(job_id) / "mapgenctl.log"


class JobLogger:
    """
    Minimal append-only job logger.

    This logger writes structured log lines to a job-specific file.
    All pipeline components should use the same format to enable
    consistent parsing and analysis.

    Attributes:
        job_id: The unique identifier for the job being logged.
        path: The filesystem path to the log file.

    Log Line Format:
        <timestamp> [job=<id>] [stage=<stage>] <LEVEL> <message>

    Example:
        >>> logger = JobLogger("abc-123")
        >>> logger.info("heightmap", "Processing started")
        # Writes: 2024-01-15T12:00:00Z [job=abc-123] [stage=heightmap] INFO Processing started
    """

    def __init__(self, job_id: str) -> None:
        """
        Initialize a logger for a specific job.

        Creates the log directory if it doesn't exist, ensuring the first
        log write won't fail due to missing directories.

        Args:
            job_id: The unique identifier for the job to log.
        """
        self.job_id = job_id
        self.path = job_log_path(job_id)
        # Ensure the logs/jobs directory exists before any writes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _ts(self) -> str:
        """
        Generate an ISO 8601 UTC timestamp for log entries.

        Uses UTC to avoid timezone ambiguity when correlating logs across
        different machines or environments.

        Returns:
            str: Timestamp in format "2024-01-15T12:00:00Z"
        """
        return (
            datetime.datetime.now(datetime.UTC)
            .isoformat(timespec="seconds")
            # Replace the verbose +00:00 suffix with the more compact Z
            .replace("+00:00", "Z")
        )

    def log(self, stage: str, level: str, message: str) -> None:
        """
        Write a structured log line to the job's log file.

        This is the core logging method that all level-specific methods
        delegate to. The format is designed to be both human-readable
        and machine-parseable.

        Args:
            stage: The pipeline stage emitting the log (e.g., "heightmap").
            level: The log severity level (e.g., "INFO", "WARN", "ERROR").
            message: The human-readable log message.

        Side Effects:
            Appends a line to the job's log file.
        """
        line = (
            f"{self._ts()} "
            f"[job={self.job_id}] "
            f"[stage={stage}] "
            f"{level.upper()} {message}\n"
        )
        # Open in append mode to preserve existing log entries
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)

    def info(self, stage: str, message: str) -> None:
        """
        Log an informational message.

        Use for normal operational messages like "Processing started"
        or "Stage complete".

        Args:
            stage: The pipeline stage emitting the log.
            message: The informational message to log.
        """
        self.log(stage, "INFO", message)

    def warn(self, stage: str, message: str) -> None:
        """
        Log a warning message.

        Use for unusual but non-fatal conditions like "Retrying after
        temporary failure" or "Using default value for missing config".

        Args:
            stage: The pipeline stage emitting the log.
            message: The warning message to log.
        """
        self.log(stage, "WARN", message)

    def error(self, stage: str, message: str) -> None:
        """
        Log an error message.

        Use for failures that prevent normal operation, like "Failed to
        read input file" or "Stage processing failed".

        Args:
            stage: The pipeline stage emitting the log.
            message: The error message to log.
        """
        self.log(stage, "ERROR", message)
