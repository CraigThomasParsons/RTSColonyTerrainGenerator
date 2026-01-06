"""
TUI (Text User Interface) components for mapgenctl.

This subpackage provides curses-based terminal UI components for monitoring
the MapGenerator pipeline in real-time.

Purpose:
    During development, watching jobs progress through the pipeline is
    essential for debugging and validation. The TUI provides a live view
    of job status, logs, and completion without leaving the terminal.

Modules:
    - views: Main curses rendering loop and UI layout
    - tailer: Real-time file tailing for log monitoring
    - merger: Event merging to handle out-of-order log entries
    - job_index: Job discovery and listing utilities
    - model: Data structures for log entries (currently minimal)

Architecture:
    The TUI uses a producer-consumer pattern:
    1. TailManager polls log files in a background thread
    2. EventMerger sorts entries by timestamp
    3. The main curses loop renders merged entries

Usage:
    The TUI is typically launched via the CLI:
        python -m mapgenctl run --width 256 --height 256 --tui
"""
