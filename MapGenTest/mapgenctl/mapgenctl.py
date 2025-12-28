#!/usr/bin/env python3
"""
mapgenctl

Developer control tool for the MapGenerator pipeline.

Responsibilities:
- Submit test jobs to the pipeline
- Inspect generated artifacts
- Watch pipeline directories
- Run end-to-end pipeline test jobs
- Provide a live progress TUI for development

This tool is intentionally filesystem-driven.
The filesystem is the source of truth for pipeline state.
"""

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

from utils.paths import stage_inbox, stage_outbox, stage_archive
from utils.paths import heightmap_inbox

# ============================================================
# Pipeline definition
# ============================================================
"""
Ordered list of logical pipeline stages.

This list defines:
- Progress display order
- Completion expectations
- Valid values for --until
"""
PIPELINE_STAGES = [
    "heightmap",
    "tiler",
    "weather",
    "treeplanter",
]

"""
Ordered list of pipeline stages.

This order defines:
- Execution expectations
- Progress display order
- Completion semantics for run_pipeline()
"""

STAGE_DIRECTORY_MAP = {
    "heightmap": "Heightmap",
    "tiler": "Tiler",
    "weather": "WeatherAnalyses",
    "treeplanter": "TreePlanter",
}


"""
Stage completion checks.

Each value is a small callable that:
- Accepts a job_id string
- Returns True if that stage has completed for the job

Lambdas are used here intentionally because:
- Each check is small
- Each check is declarative
- The table reads as a compact specification

Filesystem presence is the ONLY completion signal.

Defines how mapgenctl determines whether each pipeline stage
has completed for a given job.

Completion is determined *only* by the presence of the
authoritative output artifact in that stage's outbox.
"""
STAGE_COMPLETION_CHECKS = {
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
    inbox = heightmap_inbox()
    inbox.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())

    job = {
        "job_id": job_id,
        "map_width_in_cells": width,
        "map_height_in_cells": height,
        "requested_at_utc": (
            datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        ),
    }

    job_path = inbox / f"{job_id}.json"

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
        for stage in PIPELINE_STAGES:
            if completed[stage]:
                continue

            checker = STAGE_COMPLETION_CHECKS.get(stage)

            if checker is None:
                continue

            if checker(job_id):
                completed[stage] = True

        if not args.tui:
            for stage in PIPELINE_STAGES:
                status = "✔" if completed[stage] else "…"
                print(f"{status} {stage}")
            print()

        if completed.get(args.until):
            print("[mapgenctl] Pipeline complete")
            print(f"  final stage: {args.until}")
            print()
            return

        time.sleep(1)

# ============================================================
# Pipeline execution (TUI)
# ============================================================

def run_pipeline_tui(args) -> None:
    """
    Run the pipeline with a live curses-based TUI.

    Behavior:
    - Submits a heightmap job
    - Displays live per-stage progress
    - Updates once per second
    - Exits cleanly on completion or Ctrl+C
    """
    import curses

    def _tui(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)

        job_id = submit_heightmap_job(args.width, args.height)
        completed = {stage: False for stage in PIPELINE_STAGES}

        while True:
            stdscr.clear()

            stdscr.addstr(0, 0, "MapGenerator Pipeline")
            stdscr.addstr(1, 0, f"Job ID: {job_id}")
            stdscr.addstr(2, 0, "-" * 40)

            row = 4
            for stage in PIPELINE_STAGES:
                checker = STAGE_COMPLETION_CHECKS.get(stage)

                if not completed[stage] and checker and checker(job_id):
                    completed[stage] = True

                marker = "[✔]" if completed[stage] else "[ ]"
                stdscr.addstr(row, 2, f"{marker} {stage}")
                row += 1

            stdscr.addstr(row + 1, 0, "Press Ctrl+C to exit")
            stdscr.refresh()

            if completed.get(args.until):
                stdscr.addstr(row + 3, 0, "Pipeline complete. Press any key.")
                stdscr.refresh()
                stdscr.getch()
                return

            time.sleep(1)

    try:
        curses.wrapper(_tui)
    except KeyboardInterrupt:
        pass

# ============================================================
# Stage maintenance utilities
# ============================================================

def clean_stage(args) -> None:
    """
    Remove all files from inbox, outbox, and archive for a stage.

    Intended for development resets only.
    """
    stage = args.stage

    directories = {
        "inbox": stage_inbox(stage),
        "outbox": stage_outbox(stage),
        "archive": stage_archive(stage),
    }

    print(f"[mapgenctl] Cleaning stage: {stage}")

    for name, path in directories.items():
        if not path.exists():
            print(f"  {name}: {path} (missing, skipped)")
            continue

        removed_count = 0
        for item in path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
                removed_count += 1

        print(f"  {name}: removed {removed_count} files")

    print("[mapgenctl] Clean complete")

def watch_stage(args) -> None:
    """
    Watch inbox / outbox / archive directories for a stage.

    Polls the filesystem once per second and prints changes.
    """
    stage = args.stage

    directories = {
        "inbox": stage_inbox(stage),
        "outbox": stage_outbox(stage),
        "archive": stage_archive(stage),
    }

    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)

    print(f"[mapgenctl] Watching stage: {stage}")
    for name, path in directories.items():
        print(f"  {name}: {path}")

    previous_state = {
        name: set(path.iterdir())
        for name, path in directories.items()
    }

    try:
        while True:
            time.sleep(1)

            for name, path in directories.items():
                current_state = set(path.iterdir())
                before = previous_state[name]

                for item in sorted(current_state - before):
                    print(f"[{stage}:{name}] + {item.name}")

                for item in sorted(before - current_state):
                    print(f"[{stage}:{name}] - {item.name}")

                previous_state[name] = current_state

    except KeyboardInterrupt:
        print("\n[mapgenctl] Watch stopped")

# ============================================================
# Argument parsing
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level argument parser.

    Returns:
    - argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="mapgenctl",
        description="MapGenerator developer control CLI",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    # submit-heightmap
    submit_parser = subparsers.add_parser(
        "submit-heightmap",
        help="Submit a heightmap job into the pipeline inbox",
    )
    submit_parser.add_argument("--width", type=int, required=True)
    submit_parser.add_argument("--height", type=int, required=True)
    submit_parser.add_argument("--watch", action="store_true")

    # inspect-heightmap
    inspect_parser = subparsers.add_parser(
        "inspect-heightmap",
        help="Inspect a generated heightmap binary",
    )
    inspect_parser.add_argument("path")

    # watch
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch pipeline inbox/outbox/archive directories",
    )
    watch_parser.add_argument(
        "--stage",
        choices=["heightmap", "tiler", "treeplanter"],
        required=True,
    )

    # clean
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove all files from inbox/outbox/archive for a stage",
    )
    clean_parser.add_argument(
        "--stage",
        choices=["heightmap", "tiler", "treeplanter"],
        required=True,
    )

    # build
    build_cmd_parser = subparsers.add_parser(
        "build",
        help="Build and deploy map generator components",
    )
    build_cmd_parser.add_argument(
        "target",
        choices=["heightmap", "all"],
    )
    build_cmd_parser.add_argument("--watch", action="store_true")

    # run
    run_parser = subparsers.add_parser(
        "run",
        help="Run a full pipeline test job",
    )
    run_parser.add_argument("--width", type=int, required=True)
    run_parser.add_argument("--height", type=int, required=True)
    run_parser.add_argument(
        "--until",
        choices=PIPELINE_STAGES,
        default="treeplanter",
    )
    run_parser.add_argument(
        "--tui",
        action="store_true",
        help="Show live progress TUI",
    )

    return parser

# ============================================================
# Entry point
# ============================================================

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "submit-heightmap":
        submit_heightmap_job(args.width, args.height)
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
        if args.tui:
            run_pipeline_tui(args)
        else:
            run_pipeline(args)
        sys.exit(0)

    if args.command == "build":
        print("[mapgenctl] Build command invoked")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
