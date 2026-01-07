"""
Event merging for time-ordered log display.

This module provides a buffered event merger that collects log entries
from multiple sources and emits them in timestamp order. This handles
the inherent ordering challenges when tailing multiple files concurrently.

Purpose:
    Log entries from different pipeline stages arrive asynchronously and
    may have timestamps that are slightly out of order. The EventMerger
    buffers entries briefly and uses a heap to emit them in proper order.

Design Decisions:
    - Uses a min-heap for efficient ordering by timestamp
    - Configurable buffer size to balance memory vs. ordering accuracy
    - Configurable delay tolerance for late-arriving entries
    - Falls back to arrival time when timestamps are missing
"""

import heapq
import time


class EventMerger:
    """
    Buffered event merger that emits log entries in timestamp order.

    Entries are ingested from multiple file tailers and held briefly
    in a priority queue. The drain() method returns entries that are
    ready to display, either because:
    - They have explicit timestamps (immediately ready)
    - They've waited long enough (max_delay exceeded)
    - The buffer is full (forced drain)

    Attributes:
        buffer: A min-heap of (sort_key, entry) tuples.
        max_buffer: Maximum entries to hold before forced draining.
        max_delay: Seconds to wait for late entries before emitting.

    Example:
        >>> merger = EventMerger()
        >>> merger.ingest(entry1)
        >>> merger.ingest(entry2)
        >>> for entry in merger.drain():
        ...     print(entry.message)
    """

    def __init__(self, max_buffer: int = 200, max_delay: float = 0.5):
        """
        Initialize the event merger.

        Args:
            max_buffer: Maximum number of entries to buffer before
                       forcing a drain. Prevents unbounded memory use.
            max_delay: Maximum seconds to wait for an entry without a
                      timestamp before emitting it. Balances ordering
                      accuracy against display latency.
        """
        # The buffer is a list used as a min-heap
        self.buffer = []
        self.max_buffer = max_buffer
        self.max_delay = max_delay
        # Sequence counter for stable ordering when timestamps are equal.
        # This prevents heapq from comparing LogEntry objects directly.
        self._seq = 0

    def ingest(self, entry) -> None:
        """
        Add a log entry to the merge buffer.

        Entries are keyed by their timestamp (preferred) or arrival time
        (fallback). The heap ensures the oldest entry is always first.

        Args:
            entry: A LogEntry object to add to the buffer.
        """
        # Use timestamp for ordering when available, fall back to arrival time
        # This ensures entries without timestamps still get reasonable ordering
        key = entry.timestamp or entry.arrival_time
        # Include sequence number as tie-breaker to avoid comparing LogEntry objects.
        # Heap key is (primary_key, sequence, entry) - sequence ensures stable ordering.
        self._seq += 1
        heapq.heappush(self.buffer, (key, self._seq, entry))

    def drain(self) -> list:
        """
        Return entries that are ready to be displayed.

        An entry is ready when any of these conditions are true:
        1. Buffer overflow: buffer exceeds max_buffer (must drain)
        2. Has timestamp: entry has an explicit timestamp (order is known)
        3. Delay exceeded: entry has waited longer than max_delay

        Returns:
            List of LogEntry objects ready for display, in order.

        Note:
            Entries without timestamps are held briefly in case a
            timestamped entry arrives that should sort before them.
        """
        now = time.monotonic()
        out = []

        while self.buffer:
            # Buffer tuples are (key, seq, entry)
            key, _seq, entry = self.buffer[0]

            # Condition 1: Buffer overflow - force drain to prevent memory issues
            if len(self.buffer) > self.max_buffer:
                out.append(heapq.heappop(self.buffer)[2])
                continue

            # Condition 2: Entry has a timestamp - we know its position
            if entry.timestamp:
                out.append(heapq.heappop(self.buffer)[2])
                continue

            # Condition 3: Entry has waited long enough - emit it
            # This prevents entries without timestamps from being held forever
            if entry.arrival_time <= now - self.max_delay:
                out.append(heapq.heappop(self.buffer)[2])
                continue

            # No more entries ready - stop processing
            # Remaining entries are waiting for their delay window to expire
            break

        return out
