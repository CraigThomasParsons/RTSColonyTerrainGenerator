"""
Data models for the TUI log viewer.

This module defines data structures used throughout the TUI components.
Currently minimal, but provides a central place for shared types.

Purpose:
    Log entries from different pipeline stages need a common representation
    for merging, sorting, and display. This module defines that structure.

Note:
    This module is intentionally kept minimal. As the TUI grows in complexity,
    additional data classes (job status, stage progress, etc.) can be added here.
"""

from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class LogEntry:
    """
    Represents a single log entry from a pipeline stage.

    Attributes:
        job_id: The unique identifier for the job this entry belongs to.
        stage: The pipeline stage that emitted this log (e.g., "heightmap").
        timestamp: ISO 8601 timestamp from the log, if available.
        level: Log severity level (INFO, WARN, ERROR).
        event: Optional structured event type for machine processing.
        message: Human-readable log message.
        raw: The original parsed JSON object for debugging.
        arrival_time: Monotonic time when the entry was read (for ordering).
        seq: Sequence number within the tail session (for stable sorting).

    Purpose:
        Provides a structured representation of log data that can be:
        - Sorted by timestamp or arrival order
        - Filtered by stage or level
        - Rendered in the TUI with consistent formatting
    """
    job_id: str
    stage: str
    timestamp: Optional[str]
    level: Optional[str]
    event: Optional[str]
    message: Optional[str]
    raw: Any
    arrival_time: float
    seq: int
