#!/usr/bin/env python3
"""
mapgenctl

Developer control tool for the MapGenerator pipeline.

Responsibilities:
- Submit test jobs to the pipeline
- Inspect generated heightmap artifacts
- Act as a manual test harness for each pipeline stage

This CLI mirrors API-level contracts.
It does NOT expose engine tuning parameters.
"""

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
# Command implementations
# ============================================================
def clean_stage(args) -> None:
    """
    Remove all files from inbox, outbox, and archive for a pipeline stage.

    This is intended for test resets only.
    Directories themselves are preserved.
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
    Watch inbox / outbox / archive directories for a pipeline stage.

    Polls the filesystem and prints changes.
    """
    stage = args.stage

    directories = {
        "inbox": stage_inbox(stage),
        "outbox": stage_outbox(stage),
        "archive": stage_archive(stage),
    }

    for name, path in directories.items():
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

                added = current_state - before
                removed = before - current_state

                for item in sorted(added):
                    print(f"[{stage}:{name}] + {item.name}")

                for item in sorted(removed):
                    print(f"[{stage}:{name}] - {item.name}")

                previous_state[name] = current_state

    except KeyboardInterrupt:
        print("\n[mapgenctl] Watch stopped")

def submit_heightmap(args) -> None:
    """
    Submit a heightmap job into the Heightmap inbox.

    Inputs:
    - args.width  (int)
    - args.height (int)

    Side effects:
    - Writes a job JSON file into the heightmap inbox
    """
    inbox = heightmap_inbox()
    inbox.mkdir(parents=True, exist_ok=True)

    job = {
        "job_id": str(uuid.uuid4()),
        "map_width_in_cells": args.width,
        "map_height_in_cells": args.height,
        "requested_at_utc": (
            datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        ),
    }

    job_path = inbox / f"{job['job_id']}.json"

    with job_path.open("w", encoding="utf-8") as file:
        json.dump(job, file, indent=2)

    print("[mapgenctl] Heightmap job submitted")
    print(f"  job_id: {job['job_id']}")
    print(f"  inbox:  {job_path}")


def inspect_heightmap(args) -> None:
    """
    Inspect a generated heightmap binary file.

    Reads and validates the v1 heightmap format:

        [HEADER]
        u32 width
        u32 height
        u64 seed

        [HEIGHTMAP]
        u8 * (width * height)

        [LAYERMAP]
        u8 * (width * height)
    """
    input_path = Path(args.path).expanduser().resolve()

    # Allow passing a directory (pick latest .heightmap)
    if input_path.is_dir():
        candidates = sorted(input_path.glob("*.heightmap"))

        if not candidates:
            print(f"[mapgenctl] No .heightmap files found in {input_path}")
            sys.exit(1)

        path = candidates[-1]
    else:
        path = input_path

    if not path.exists():
        print(f"[mapgenctl] File not found: {path}")
        sys.exit(1)

    if path.suffix != ".heightmap":
        print(f"[mapgenctl] Not a .heightmap file: {path}")
        sys.exit(1)

    file_size = path.stat().st_size

    if file_size < 16:
        print("[mapgenctl] Invalid heightmap file: too small to contain header")
        sys.exit(1)

    # Read header
    with path.open("rb") as file:
        header_bytes = file.read(16)

        if len(header_bytes) != 16:
            print("[mapgenctl] Invalid heightmap file: incomplete header")
            sys.exit(1)

        width, height, seed = struct.unpack("<IIQ", header_bytes)

    cell_count = width * height
    expected_size = 16 + (cell_count * 2)

    print("[mapgenctl] Heightmap inspection")
    print(f"  path:        {path}")
    print(f"  width:       {width}")
    print(f"  height:      {height}")
    print(f"  seed:        {seed}")
    print(f"  cells:       {cell_count}")
    print(f"  file size:   {file_size} bytes")
    print(f"  expected:    {expected_size} bytes")

    if file_size != expected_size:
        print("  WARNING: file size does not match expected layout")
    else:
        print("  layout:      OK")


# ============================================================
# Argument parsing
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level CLI argument parser.
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

    # ------------------------------------------------------------
    # submit-heightmap
    # ------------------------------------------------------------
    submit_parser = subparsers.add_parser(
        "submit-heightmap",
        help="Submit a heightmap job into the pipeline inbox",
    )

    submit_parser.add_argument(
        "--width",
        type=int,
        required=True,
        help="Map width in cells",
    )

    submit_parser.add_argument(
        "--height",
        type=int,
        required=True,
        help="Map height in cells",
    )

    submit_parser.add_argument(
        "--watch",
        action="store_true",
        help="After submitting, watch directories and logs",
    )


    # ------------------------------------------------------------
    # inspect-heightmap
    # ------------------------------------------------------------
    inspect_parser = subparsers.add_parser(
        "inspect-heightmap",
        help="Inspect a generated heightmap binary",
    )

    inspect_parser.add_argument(
        "path",
        help="Path to .heightmap file or directory",
    )

    # ------------------------------------------------------------
    # watch
    # ------------------------------------------------------------
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

    build_parser = subparsers.add_parser(
        "build",
        help="Build and deploy map generator components"
    )

    build_parser.add_argument(
        "component",
        choices=["heightmap"],
        help="Component to build"
    )

    return parser

# ============================================================
# Test and Watch 
# ============================================================
def watch_heightmap_test_run() -> None:
    print("\n[mapgenctl] Watching heightmap test run")
    print("Press Ctrl+C to stop\n")

    log_thread = threading.Thread(
        target=tail_systemd_logs,
        args=("heightmap-queue.service",),
        daemon=True,
    )

    log_thread.start()

    try:
        watch_stage(
            argparse.Namespace(stage="heightmap")
        )
    except KeyboardInterrupt:
        print("\n[mapgenctl] Test watch stopped")



# ============================================================
# Tail the systemd logs to find any potential error logs.
# ============================================================

def tail_systemd_logs(unit_name: str) -> None:
    try:
        subprocess.run(
            [
                "journalctl",
                "--user",
                "-u",
                unit_name,
                "-f",
                "--no-pager",
            ],
            check=False,
        )
    except FileNotFoundError:
        print("[mapgenctl] journalctl not found; skipping logs")

def build_heightmap_engine():
    repo_root = Path(__file__).resolve().parents[2]

    engine_dir = (
        repo_root
        / "MapGenerator"
        / "Heightmap"
        / "heightmap-engine"
    )

    bin_dir = (
        repo_root
        / "MapGenerator"
        / "Heightmap"
        / "bin"
    )

    built_binary = (
        engine_dir
        / "target"
        / "release"
        / "heightmap-engine"
    )

    deployed_binary = bin_dir / "heightmap-engine"

    print("[mapgenctl] Building heightmap engine (release)")
    print(f"  source: {engine_dir}")

    subprocess.run(
        ["cargo", "build", "--release"],
        cwd=engine_dir,
        check=True,
    )

    if not built_binary.exists():
        print("[mapgenctl] ❌ Build succeeded but binary not found")
        sys.exit(1)

    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_binary, deployed_binary)
    deployed_binary.chmod(0o755)

    print("[mapgenctl] ✅ Heightmap engine deployed")
    print(f"  binary: {deployed_binary}")

# ============================================================
# Entry point
# ============================================================

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "submit-heightmap":
        submit_heightmap(args)

        if args.watch:
            watch_heightmap_test_run()

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

    if args.command == "build":
        if args.component == "heightmap":
            build_heightmap_engine()
        else:
            print(f"[mapgenctl] Unknown build target: {args.component}")
            sys.exit(1)
        sys.exit(0)

    # Defensive fallback
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
