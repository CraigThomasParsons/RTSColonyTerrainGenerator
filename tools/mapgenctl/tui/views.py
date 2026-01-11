"""
Curses-based UI views for log monitoring.

This module contains the main rendering loop for the TUI log viewer.
It combines the file tailer and event merger to display a live stream
of log entries in the terminal.

Purpose:
    Developers need to see what's happening in the pipeline as jobs run.
    This viewer provides a scrolling, real-time display of log entries
    from all stages of a running job.

Architecture:
    - Background thread: Polls log files via TailManager
    - Main thread: Merges events and renders via curses
    - Communication: Thread-safe queue between producer and consumer
"""

import curses
import threading
import time
from collections import deque
from queue import Queue, Empty

from .tailer import TailManager
from .merger import EventMerger


def run_log_viewer(stdscr, job_id: str) -> None:
    """
    Run the interactive log viewer TUI.

    This is the main entry point for the log viewer. It sets up the
    curses environment, starts the background tailer thread, and runs
    the main rendering loop until the user exits.

    Args:
        stdscr: The curses standard screen object (provided by curses.wrapper).
        job_id: The job ID to monitor and display logs for.

    Side Effects:
        - Creates a background thread for file tailing
        - Takes over the terminal until the user presses 'q' or Ctrl+C

    Note:
        This function should be called via curses.wrapper() to ensure
        proper terminal setup and cleanup.
    """
    # Hide the cursor for a cleaner UI
    curses.curs_set(0)
    # Enable non-blocking getch() so we can poll for input
    stdscr.nodelay(True)

    # --- Runtime state ---
    # Flag to signal the background thread to stop
    running = True
    # Thread-safe queue for passing entries from tailer to renderer
    log_queue: Queue = Queue(maxsize=2000)
    # Merger to sort entries by timestamp before display
    merger = EventMerger()
    # Rolling buffer of formatted log lines for display
    # maxlen prevents unbounded memory growth for long-running sessions
    visible_lines = deque(maxlen=500)

    # Create the tail manager for monitoring log files
    tailer = TailManager(job_id, log_queue)

    # --- Background tail thread ---
    # Run file polling in a separate thread to avoid blocking the UI
    def tail_loop():
        """Background thread: poll log files and push entries to queue."""
        while running:
            tailer.tick()
            # Poll every 250ms - balance between responsiveness and CPU usage
            time.sleep(0.25)

    # Start the background thread as a daemon so it dies with the main thread
    thread = threading.Thread(target=tail_loop, daemon=True)
    thread.start()

    # --- Main UI loop ---
    while running:
        try:
            # Handle user input
            ch = stdscr.getch()
            # Exit on 'q', 'Q', or Ctrl+C (character code 3)
            if ch in (ord("q"), ord("Q"), 3):
                running = False
                break

            # Drain entries from the tail queue into the merger
            # Non-blocking loop to process all available entries
            while True:
                entry = log_queue.get_nowait()
                merger.ingest(entry)
        except Empty:
            # No more entries in queue - continue to rendering
            pass

        # Get merged entries (sorted by timestamp) and format for display
        for entry in merger.drain():
            # Format each entry as a single display line
            # Use placeholder for missing timestamp
            ts = entry.timestamp or "--------"
            stage = entry.stage or "unknown"
            level = (entry.level or "info").upper()
            msg = entry.message or ""
            line = f"{ts} {stage:<12} {level:<5} {msg}"
            visible_lines.append(line)

        # --- Render the screen ---
        # Clear previous frame
        stdscr.erase()
        # Get current terminal dimensions
        h, w = stdscr.getmaxyx()

        # Draw header
        stdscr.addstr(0, 0, f"MapGenCtrl Log Viewer — Job {job_id}")
        stdscr.addstr(1, 0, "-" * (w - 1))

        # Calculate which lines to display (tail of the buffer)
        # Leave room for header (2 lines) and footer (1 line)
        start = max(0, len(visible_lines) - (h - 3))
        # Draw log lines, truncating to screen width
        for idx, line in enumerate(list(visible_lines)[start:], start=2):
            # Stop if we've filled the screen
            if idx >= h:
                break
            # Truncate line to fit terminal width
            stdscr.addstr(idx, 0, line[: w - 1])

        # Draw footer with exit instructions
        stdscr.addstr(h - 1, 0, "Press q or Ctrl+C to exit")
        # Push frame to terminal
        stdscr.refresh()

        # Brief sleep to cap frame rate and reduce CPU usage
        # 50ms = ~20 FPS, smooth enough for log viewing
        time.sleep(0.05)

    # Allow tail thread to finish its current iteration before exiting
    time.sleep(0.1)
