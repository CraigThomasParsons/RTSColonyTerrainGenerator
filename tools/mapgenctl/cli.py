#!/usr/bin/env python3
"""
mapgenctl - Developer Control Tool for the MapGenerator Pipeline.

This module implements the command-line interface for mapgenctl, providing
commands to submit jobs, monitor progress, inspect outputs, and manage
pipeline state during development.

Responsibilities:
    - Submit test jobs to the pipeline (submit-heightmap, run)
    - Inspect generated artifacts (inspect-heightmap)
    - Watch pipeline directories for changes (watch)
    - Run end-to-end pipeline test jobs with progress tracking (run)
    - Provide a live progress TUI for development (run --tui)
    - Clean up pipeline state (clean)

Design Philosophy:
    This tool is intentionally filesystem-driven. The filesystem is the
    single source of truth for pipeline state. This means:
    - No database or external services required
    - State can be inspected with standard Unix tools (ls, cat, etc.)
    - Easy to debug and understand what's happening
    - Simple deployment (just files and directories)

Usage:
    python -m mapgenctl <command> [options]

Examples:
    python -m mapgenctl submit-heightmap --width 256 --height 256
    python -m mapgenctl run --width 256 --height 256 --tui
    python -m mapgenctl watch --stage heightmap
    python -m mapgenctl clean --stage heightmap
"""

# Standard library imports
import os
import argparse
import sys
import json
import uuid
import datetime
import struct
import time
import subprocess
import threading
import shutil

from pathlib import Path

# Local imports - utilities for path resolution and logging
from .utils.paths import stage_inbox, stage_outbox, stage_archive, heightmap_inbox
from .utils.joblog import JobLogger, job_log_path
# TUI view for the log viewer command
from .tui.views import run_log_viewer

# ============================================================
# Pipeline Definition
# ============================================================
# These constants define the structure and behavior of the pipeline.
# They are the source of truth for stage ordering and completion logic.

# Ordered list of logical pipeline stages.
# This order is significant:
#   - Progress displays follow this sequence
#   - --until flag validates against this list
#   - Completion checking iterates in this order
PIPELINE_STAGES = [
    "heightmap",      # Entry point: generates terrain height data
    "tiler",          # Slices heightmap into manageable tiles
    "weather",        # Calculates slope, flow, and basin data
    "treeplanter",    # Places vegetation based on environmental data
]

# Maps logical stage names to their filesystem directory names.
# Logical names are lowercase for CLI convenience, but the actual
# directories use title case to match project conventions.
STAGE_DIRECTORY_MAP = {
    "heightmap": "Heightmap",
    "tiler": "Tiler",
    "weather": "WeatherAnalyses",  # Note: not "Weather" - full name used
    "treeplanter": "TreePlanter",
}


# Stage completion checks - determines when each stage has finished.
#
# Why lambdas? Each check is:
#   - Small and self-contained (one expression)
#   - Declarative (describes what, not how)
#   - The table reads as a compact specification
#
# Why file presence? The filesystem is the source of truth:
#   - No need for inter-process communication
#   - Can be verified with `ls` or `test -f`
#   - Survives process crashes (no in-memory state to lose)
#   - Each stage knows its own output filename convention
STAGE_COMPLETION_CHECKS = {
    # Each stage produces a specific artifact type with a known extension
    "heightmap": lambda job_id: (
        resolved_stage_outbox("heightmap") / f"{job_id}.heightmap"
    ).exists(),

    "tiler": lambda job_id: (
        resolved_stage_outbox("tiler") / f"{job_id}.maptiles"
    ).exists(),

    "weather": lambda job_id: (
        resolved_stage_outbox("weather") / f"{job_id}.weather"
    ).exists(),

    "treeplanter": lambda job_id: (
        resolved_stage_outbox("treeplanter") / f"{job_id}.worldpayload"
    ).exists(),
}

# ============================================================
# Environment Configuration
# ============================================================

def load_dotenv() -> None:
    """
    Load the repository-root .env file into os.environ if present.

    This enables developers to configure paths and other settings via
    a .env file at the repository root, without modifying system
    environment variables.

    Side Effects:
        Modifies os.environ by adding any variables from .env that
        aren't already set (uses setdefault, so existing vars win).

    Note:
        We implement our own .env loading rather than using python-dotenv
        to avoid adding an external dependency for a simple feature.
    """
    from pathlib import Path

    # Navigate to repo root: cli.py -> mapgenctl/ -> tools/ -> repo/
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"

    # Silently skip if no .env file exists - it's optional
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Skip malformed lines (no = sign)
            if "=" not in line:
                continue
            # Split on first = only (value might contain =)
            key, value = line.split("=", 1)
            # setdefault ensures existing env vars take priority
            os.environ.setdefault(key, value)


def resolved_stage_outbox(stage: str) -> Path:
    """
    Resolve the authoritative outbox directory for a logical pipeline stage.

    Inputs:
    - stage (str): logical pipeline stage identifier

    Returns:
    - Path to that stage's outbox directory
    """
    directory_name = STAGE_DIRECTORY_MAP.get(stage)

    if directory_name is None:
        raise KeyError(f"Unknown pipeline stage: {stage}")

    return Path(
        f"~/Code/RTSColonyTerrainGenerator/MapGenerator/{directory_name}/outbox"
    ).expanduser()


# ============================================================
# Job submission helpers
# ============================================================

def submit_heightmap_job(width: int, height: int) -> str:
    """
    Submit a heightmap generation job.

    Inputs:
    - width: map width in cells
    - height: map height in cells

    Side effects:
    - Writes a JSON job file into the heightmap inbox

    Returns:
    - job_id (str): the generated job identifier
    """
    # Locate the inbox for the heightmap stage
    inbox = heightmap_inbox()
    # Ensure the directory exists before writing so we don't crash
    inbox.mkdir(parents=True, exist_ok=True)

    # Generate a unique identifier for this job to track it through the pipeline
    job_id = str(uuid.uuid4())

    # Construct the job payload with all required parameters
    job = {
        "job_id": job_id,
        "map_width_in_cells": width,
        "map_height_in_cells": height,
        # Timestamp the request for observability and debugging
        "requested_at_utc": (
            datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds") + "Z"
        ),
    }

    # Define the full path for the job file
    job_path = inbox / f"{job_id}.json"

    # Write the job file atomically (or as close as possible with a single write)
    with job_path.open("w", encoding="utf-8") as file:
        json.dump(job, file, indent=2)

    return job_id

# ============================================================
# Pipeline execution (non-TUI)
# ============================================================

def run_pipeline(args) -> None:
    """
    Run an end-to-end pipeline test job.

    Behavior:
    - Submits a heightmap job
    - Polls the filesystem for stage completion
    - Prints simple textual progress
    - Stops when the requested stage is complete

    Inputs:
    - args.width
    - args.height
    - args.until
    - args.tui (must be False here)
    """
    job_id = submit_heightmap_job(args.width, args.height)

    print("[mapgenctl] Pipeline run started")
    print(f"  job_id: {job_id}")
    print(f"  until:  {args.until}")
    print()

    completed = {stage: False for stage in PIPELINE_STAGES}

    while True:
        # Check completion status for all stages
        for stage in PIPELINE_STAGES:
            # Skip stages we already know are done
            if completed[stage]:
                continue

            # Get the specific check logic for this stage
            checker = STAGE_COMPLETION_CHECKS.get(stage)

            # If no check is defined, skip it
            if checker is None:
                continue

            # Run the check against the filesystem
            if checker(job_id):
                completed[stage] = True

        # Update the console output if we are NOT in TUI mode
        if not args.tui:
            for stage in PIPELINE_STAGES:
                # Use a checkmark for done, dots for waiting
                status = "✔" if completed[stage] else "…"
                print(f"{status} {stage}")
            print()

        # Check if we have reached the target stage
        if completed.get(args.until):
            print("[mapgenctl] Pipeline complete")
            print(f"  final stage: {args.until}")
            print()
            return

        # Wait a bit before polling again to save CPU
        # 1 second is a reasonable balance between responsiveness and efficiency
        time.sleep(1)


# ============================================================
# Utility Functions
# ============================================================

def tail_last_lines(path: Path, max_lines: int = 8) -> list[str]:
    """
    Tail the last N lines of a text file safely.

    This is a simple implementation that reads the whole file. For small
    development logs, this is fine. If performance becomes an issue with
    large files, we can optimize to read backwards from the end.

    Args:
        path: Path to the text file to tail.
        max_lines: Maximum number of lines to return (default: 8).

    Returns:
        List of the last N lines from the file, or empty list if
        the file doesn't exist or can't be read.

    Note:
        Errors are silently handled - this is intentional for the TUI
        use case where missing/unreadable logs shouldn't crash the UI.
    """
    # Return empty list for missing files (stage might not have started)
    if not path.exists():
        return []

    try:
        # errors="replace" handles any encoding issues gracefully
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        # File might be locked or have permission issues - fail gracefully
        return []

    lines = text.splitlines()
    # Python slicing handles the case where we have fewer lines than max_lines
    return lines[-max_lines:]

# ============================================================
# Pipeline execution (TUI)
# ============================================================

def run_pipeline_tui(args) -> None:
    """
    Run the pipeline with a live curses-based TUI.

    Upgrades:
    - Writes to a single job log file
    - Shows spinner on active stage
    - Tails last lines of the log under the UI
    """
    import curses

    from .utils.joblog import JobLogger, job_log_path


    SPINNER = ["|", "/", "-", "\\"]  # safest everywhere

    def _tui(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)

        job_id = submit_heightmap_job(args.width, args.height)
        logger = JobLogger(job_id)
        log_path = job_log_path(job_id)

        logger.info("mapgenctl", f"Job submitted width={args.width} height={args.height} until={args.until}")

        completed = {stage: False for stage in PIPELINE_STAGES}
        spinner_i = 0

        while True:
            # allow Ctrl+C-ish behavior (q is nice too)
            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                logger.warn("mapgenctl", "User requested exit (q)")
                return

            # update completion status
            for stage in PIPELINE_STAGES:
                if completed[stage]:
                    continue
                checker = STAGE_COMPLETION_CHECKS.get(stage)
                if checker and checker(job_id):
                    completed[stage] = True
                    logger.info(stage, "Stage complete (artifact detected)")

            # determine active stage = first incomplete up to args.until
            active_stage = None
            for stage in PIPELINE_STAGES:
                if stage == args.until and completed.get(stage):
                    active_stage = None
                    break
                if not completed.get(stage):
                    active_stage = stage
                    break

            # render frame
            stdscr.clear()
            stdscr.addstr(0, 0, "MapGenerator Pipeline")
            stdscr.addstr(1, 0, f"Job ID: {job_id}")
            stdscr.addstr(2, 0, "-" * 50)

            row = 4
            for stage in PIPELINE_STAGES:
                # status marker
                if completed[stage]:
                    marker = "[✔]"
                    right = "done"
                elif stage == active_stage:
                    marker = f"[{SPINNER[spinner_i]}]"
                    right = "running"
                else:
                    marker = "[ ]"
                    right = ""

                # stage line
                stdscr.addstr(row, 2, f"{marker} {stage:<12} {right}")
                row += 1

                if stage == args.until:
                    break

            stdscr.addstr(row + 1, 0, "Press Ctrl+C (or q) to exit")
            stdscr.addstr(row + 2, 0, "-" * 50)
            stdscr.addstr(row + 3, 0, f"Logs (job={job_id}):")

            # tail log
            log_lines = tail_last_lines(log_path, max_lines=8)
            for i, line in enumerate(log_lines):
                # defensive: don't overflow screen width
                try:
                    stdscr.addstr(row + 4 + i, 0, line[: max(0, curses.COLS - 1)])
                except curses.error:
                    pass

            stdscr.refresh()

            # completion
            if completed.get(args.until):
                logger.info("mapgenctl", f"Pipeline reached target stage: {args.until}")
                stdscr.addstr(row + 13, 0, "Pipeline complete. Press any key.")
                stdscr.nodelay(False)
                stdscr.getch()
                return

            spinner_i = (spinner_i + 1) % len(SPINNER)
            time.sleep(0.1)

    try:
        curses.wrapper(_tui)
    except KeyboardInterrupt:
        # let Ctrl+C exit cleanly
        pass

# ============================================================
# Stage Maintenance Utilities
# ============================================================
# These functions help developers reset pipeline state during development.


def clean_stage(args) -> None:
    """
    Remove all files from inbox, outbox, and archive for a stage.

    This is a destructive operation intended for development use only.
    It's useful when you want to re-run the pipeline from scratch or
    clear out failed job artifacts.

    Args:
        args: Namespace with 'stage' attribute specifying which
              pipeline stage to clean (e.g., "heightmap").

    Side Effects:
        - Deletes all files in the stage's inbox, outbox, and archive
        - Prints progress to stdout

    Warning:
        This permanently deletes files. There is no undo.
    """
    stage = args.stage

    # Map of directory names to their paths for iteration
    directories = {
        "inbox": stage_inbox(stage),
        "outbox": stage_outbox(stage),
        "archive": stage_archive(stage),
    }

    print(f"[mapgenctl] Cleaning stage: {stage}")

    for name, path in directories.items():
        # Skip directories that don't exist (might not have been created yet)
        if not path.exists():
            print(f"  {name}: {path} (missing, skipped)")
            continue

        removed_count = 0
        for item in path.iterdir():
            # Only remove files and symlinks, not subdirectories
            # This is a safety measure to prevent accidental damage
            if item.is_file() or item.is_symlink():
                item.unlink()
                removed_count += 1

        print(f"  {name}: removed {removed_count} files")

    print("[mapgenctl] Clean complete")

def watch_stage(args) -> None:
    """
    Watch inbox/outbox/archive directories for a stage and report changes.

    This is useful for debugging pipeline behavior. You can see in real-time
    when jobs enter a stage, when outputs are produced, and when inputs are
    archived.

    Args:
        args: Namespace with 'stage' attribute specifying which
              pipeline stage to watch (e.g., "heightmap").

    Side Effects:
        - Creates stage directories if they don't exist
        - Prints file additions/removals to stdout in real-time
        - Runs until interrupted with Ctrl+C

    Output Format:
        [stage:directory] + filename  (file added)
        [stage:directory] - filename  (file removed)
    """
    stage = args.stage

    # Define all directories to watch for this stage
    directories = {
        "inbox": stage_inbox(stage),
        "outbox": stage_outbox(stage),
        "archive": stage_archive(stage),
    }

    # Ensure all directories exist so we can watch them
    # This prevents errors on first run before pipeline creates them
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)

    print(f"[mapgenctl] Watching stage: {stage}")
    for name, path in directories.items():
        print(f"  {name}: {path}")

    # Initialize with current state to avoid false "new file" reports
    previous_state = {
        name: set(path.iterdir())
        for name, path in directories.items()
    }

    try:
        # Main polling loop - runs until Ctrl+C
        while True:
            # Poll every second - balances responsiveness vs. CPU usage
            time.sleep(1)

            for name, path in directories.items():
                # Get current directory contents
                current_state = set(path.iterdir())
                before = previous_state[name]

                # Set difference to find new files (in current but not before)
                for item in sorted(current_state - before):
                    print(f"[{stage}:{name}] + {item.name}")

                # Set difference to find removed files (in before but not current)
                for item in sorted(before - current_state):
                    print(f"[{stage}:{name}] - {item.name}")

                # Update state for next iteration
                previous_state[name] = current_state

    except KeyboardInterrupt:
        # Clean exit message when user presses Ctrl+C
        print("\n[mapgenctl] Watch stopped")

# ============================================================
# Command-Line Argument Parsing
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build and configure the top-level argument parser.

    This function defines all CLI subcommands and their arguments.
    Subcommands are organized by use case:
        - Job submission: submit-heightmap, run
        - Monitoring: watch, logs
        - Debugging: inspect-heightmap
        - Maintenance: clean, build

    Returns:
        argparse.ArgumentParser: Configured parser ready to parse sys.argv.

    Note:
        This uses argparse's subparser feature for clean command separation.
        Each subcommand gets its own help text and argument validation.
    """
    parser = argparse.ArgumentParser(
        prog="mapgenctl",
        description="MapGenerator developer control CLI",
    )

    # Create subparser container for all commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,  # User must specify a command
    )

    # --- submit-heightmap: Quick job submission ---
    submit_parser = subparsers.add_parser(
        "submit-heightmap",
        help="Submit a heightmap job into the pipeline inbox",
    )
    submit_parser.add_argument("--width", type=int, required=True,
                               help="Map width in cells")
    submit_parser.add_argument("--height", type=int, required=True,
                               help="Map height in cells")
    submit_parser.add_argument("--watch", action="store_true",
                               help="Watch for completion after submitting")

    # --- inspect-heightmap: Debug output artifacts ---
    inspect_parser = subparsers.add_parser(
        "inspect-heightmap",
        help="Inspect a generated heightmap binary",
    )
    inspect_parser.add_argument("path", help="Path to .heightmap file")

    # --- watch: Real-time directory monitoring ---
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch pipeline inbox/outbox/archive directories",
    )
    watch_parser.add_argument(
        "--stage",
        choices=["heightmap", "tiler", "treeplanter"],
        required=True,
        help="Pipeline stage to watch",
    )

    # --- clean: Reset pipeline state ---
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove all files from inbox/outbox/archive for a stage",
    )
    clean_parser.add_argument(
        "--stage",
        choices=["heightmap", "tiler", "treeplanter"],
        required=True,
        help="Pipeline stage to clean",
    )

    # --- build: Compile pipeline components ---
    build_cmd_parser = subparsers.add_parser(
        "build",
        help="Build and deploy map generator components",
    )
    build_cmd_parser.add_argument(
        "target",
        choices=["heightmap", "all"],
        help="Component to build",
    )
    build_cmd_parser.add_argument("--watch", action="store_true",
                                  help="Rebuild on file changes")

    # --- logs: TUI log viewer ---
    log_parser = subparsers.add_parser(
        "logs",
        help="Tail logs for a job ID (TUI)",
    )
    log_parser.add_argument("job_id", help="UUID of job to view logs for")

    # --- run: Full pipeline execution ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run a full pipeline test job",
    )
    run_parser.add_argument("--width", type=int, required=True,
                            help="Map width in cells")
    run_parser.add_argument("--height", type=int, required=True,
                            help="Map height in cells")
    run_parser.add_argument(
        "--until",
        choices=PIPELINE_STAGES,
        default="treeplanter",
        help="Stop after this stage completes (default: treeplanter)",
    )
    run_parser.add_argument(
        "--tui",
        action="store_true",
        help="Show live progress TUI instead of text output",
    )

    return parser


def inspect_heightmap(args) -> None:
    """
    Inspect and display information about a heightmap binary file.

    Args:
        args: Namespace with 'path' attribute pointing to a .heightmap file.

    Raises:
        NotImplementedError: This feature is planned but not yet implemented.

    TODO:
        - Parse binary header format
        - Display dimensions, metadata, and sample values
        - Optionally render ASCII visualization
    """
    raise NotImplementedError

# ============================================================
# Entry Point
# ============================================================

def main() -> None:
    """
    Main entry point for the mapgenctl CLI.

    This function:
    1. Loads environment configuration from .env
    2. Parses command-line arguments
    3. Dispatches to the appropriate command handler

    Exit Codes:
        0: Success
        1: Invalid command or error
    """
    # Load any .env configuration before parsing args
    load_dotenv()

    # Parse command-line arguments
    parser = build_parser()
    args = parser.parse_args()

    # --- Command dispatch ---
    # Each command handler is responsible for its own logic.
    # We use explicit if statements rather than a dispatch table
    # for clarity and to allow custom handling per command.

    if args.command == "submit-heightmap":
        job_id = submit_heightmap_job(args.width, args.height)
        print(f"Submitted job: {job_id}")

        if args.watch:
            # Create a minimal args object for watch_stage
            # This is a quick inline class rather than a full Args definition
            class WatchArgs:
                stage = "heightmap"
            print("Watching for job completion...")
            watch_stage(WatchArgs())

        sys.exit(0)

    if args.command == "inspect-heightmap":
        inspect_heightmap(args)
        sys.exit(0)

    if args.command == "watch":
        watch_stage(args)
        sys.exit(0)

    if args.command == "clean":
        clean_stage(args)
        sys.exit(0)

    if args.command == "run":
        # Choose between TUI and simple text output based on --tui flag
        if args.tui:
            run_pipeline_tui(args)
        else:
            run_pipeline(args)
        sys.exit(0)

    if args.command == "logs":
        import curses
        curses.wrapper(run_log_viewer, args.job_id)
        sys.exit(0)

    if args.command == "build":
        # Placeholder - build functionality to be implemented
        print("[mapgenctl] Build command invoked")
        sys.exit(0)

    # Unknown command - show help
    parser.print_help()
    sys.exit(1)


# Standard Python idiom: only run main() if this file is executed directly
if __name__ == "__main__":
    main()
