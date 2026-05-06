#!/usr/bin/env python3
"""
Playable stage engine.

This stage turns a worldpayload into a minimally playable layout by selecting
deterministic start zones and nearby resource hints. It is intentionally simple
and conservative to keep the pipeline stable while enabling downstream exports.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class JobSelection:
    job_id: str
    input_path: Path
    output_path: Path


# These constants express playability constraints in a stable, deterministic way.
# They trade precision for clarity to avoid hidden complexity in early iterations.
PASSABLE_TERRAINS = {"grass", "rock"}
SLOPE_THRESHOLD = 6000
MIN_START_SEPARATION = 24


def log_line(log_file: Path, job_id: str, level: str, message: str) -> None:
    """
    Description:
        Write a structured log line for the current job and emit it to stdout.
    Required State:
        - log_file must be a writable path on disk.
    Usage:
        Call for every significant event to keep pipeline tracing consistent.
    Parameters:
        log_file (Path): Destination log file path.
        job_id (str): Job identifier used for log correlation.
        level (str): Log severity (INFO/WARN/ERROR).
        message (str): Human-readable explanation of the event.
    Returns:
        None: Logging is a side effect only.
    Other I/O:
        - files: appends to log_file
        - stdout: prints the log line
    """
    # Use UTC timestamps for consistency across pipeline logs.
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{timestamp} [job={job_id}] [stage=playable] {level} {message}"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def iter_candidate_payloads(input_dir: Path) -> Iterable[Path]:
    """
    Description:
        List potential worldpayload inputs from a directory.
    Required State:
        - input_dir should exist or the caller should handle empty results.
    Usage:
        Use before selecting the latest unprocessed job.
    Parameters:
        input_dir (Path): Directory that stores worldpayload artifacts.
    Returns:
        Iterable[Path]: Candidate payload paths (files or directories).
    Other I/O:
        - files: reads directory entries
    """
    # Return empty when the directory is missing to avoid raising in path units.
    if not input_dir.exists():
        return []
    return [
        path
        for path in input_dir.iterdir()
        if path.name.endswith(".worldpayload") or path.is_dir()
    ]


def select_job(input_dir: Path, output_dir: Path, job_id: Optional[str]) -> Optional[JobSelection]:
    """
    Description:
        Select the next worldpayload to process, preferring explicit job_id.
    Required State:
        - input_dir points at upstream payload artifacts.
        - output_dir is writable to avoid silent failures.
    Usage:
        Call once per worker invocation to claim a single job.
    Parameters:
        input_dir (Path): Upstream payload directory.
        output_dir (Path): Destination payload directory.
        job_id (Optional[str]): Explicit job identifier if provided.
    Returns:
        Optional[JobSelection]: Selection metadata or None when no work exists.
    Other I/O:
        - files: reads directory metadata for modification times
    """
    if job_id:
        candidate = input_dir / f"{job_id}.worldpayload"
        if candidate.exists():
            output_path = output_dir / candidate.name
            return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)
        candidate_dir = input_dir / job_id
        if candidate_dir.exists():
            output_path = output_dir / candidate_dir.name
            return JobSelection(job_id=job_id, input_path=candidate_dir, output_path=output_path)
        # Explicit job selection failed, so return None to avoid guessing.
        return None

    candidates = list(iter_candidate_payloads(input_dir))
    if not candidates:
        return None

    # Prefer the newest payload so repeated triggers process recent work.
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        job_name = candidate.name
        job_id = job_name.replace(".worldpayload", "")
        output_path = output_dir / job_name
        if output_path.exists():
            # Skip work that has already been emitted.
            continue
        return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)

    return None


def copy_payload(source: Path, destination: Path) -> None:
    """
    Description:
        Copy a payload file or directory tree into the destination.
    Required State:
        - source must exist and be readable.
        - destination parent must be writable.
    Usage:
        Use for directory-style payloads that should be preserved as-is.
    Parameters:
        source (Path): Source payload file or directory.
        destination (Path): Destination path for the copied payload.
    Returns:
        None: The copy is performed as a side effect.
    Other I/O:
        - files: reads from source, writes to destination
    """
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = destination / item.name
            if item.is_dir():
                copy_payload(item, target)
            else:
                target.write_bytes(item.read_bytes())
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())


def compute_bounds(tiles: List[Dict[str, object]]) -> Tuple[int, int]:
    """
    Description:
        Compute the max tile coordinates to infer map extents.
    Required State:
        - tiles should contain integer-like x/y values.
    Usage:
        Call once to clamp placement targets within bounds.
    Parameters:
        tiles (List[Dict[str, object]]): Tile dictionaries from the payload.
    Returns:
        Tuple[int, int]: (max_x, max_y) coordinate bounds.
    Other I/O:
        None.
    """
    max_x = 0
    max_y = 0
    for tile in tiles:
        try:
            x = int(tile.get("x", 0))
            y = int(tile.get("y", 0))
        except (TypeError, ValueError):
            # Skip malformed tiles to avoid breaking the pipeline.
            continue
        if x > max_x:
            max_x = x
        if y > max_y:
            max_y = y
    return max_x, max_y


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """
    Description:
        Compute Manhattan distance to enforce minimum start separation.
    Required State:
        - a and b are (x, y) tuples.
    Usage:
        Use for cheap distance checks without pathfinding.
    Parameters:
        a (Tuple[int, int]): First coordinate.
        b (Tuple[int, int]): Second coordinate.
    Returns:
        int: Manhattan distance between a and b.
    Other I/O:
        None.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def tile_is_passable(tile: Dict[str, object]) -> bool:
    """
    Description:
        Decide whether a tile is viable for starts/resources.
    Required State:
        - tile contains terrain and optional weather.slope data.
    Usage:
        Use as a gate to keep placement on safe, walkable terrain.
    Parameters:
        tile (Dict[str, object]): Tile metadata from the payload.
    Returns:
        bool: True if terrain and slope are acceptable for placement.
    Other I/O:
        None.
    """
    terrain = tile.get("terrain")
    if terrain not in PASSABLE_TERRAINS:
        return False
    weather = tile.get("weather") or {}
    slope = weather.get("slope", 0)
    try:
        slope_value = int(slope)
    except (TypeError, ValueError):
        slope_value = 0
    return slope_value <= SLOPE_THRESHOLD


def build_passable_index(tiles: List[Dict[str, object]]) -> Dict[Tuple[int, int], Dict[str, object]]:
    """
    Description:
        Build a lookup of passable tiles keyed by coordinate.
    Required State:
        - tiles include integer-like x/y values.
    Usage:
        Use to find nearby valid placement targets cheaply.
    Parameters:
        tiles (List[Dict[str, object]]): Tile metadata from the payload.
    Returns:
        Dict[Tuple[int, int], Dict[str, object]]: Passable tile index.
    Other I/O:
        None.
    """
    index: Dict[Tuple[int, int], Dict[str, object]] = {}
    for tile in tiles:
        try:
            x = int(tile.get("x", 0))
            y = int(tile.get("y", 0))
        except (TypeError, ValueError):
            # Skip malformed tiles to keep placement deterministic.
            continue
        if tile_is_passable(tile):
            index[(x, y)] = tile
    return index


def find_nearest_passable(
    target: Tuple[int, int],
    passable_index: Dict[Tuple[int, int], Dict[str, object]],
    max_radius: int,
) -> Tuple[int, int]:
    """
    Description:
        Locate the closest passable coordinate to a target.
    Required State:
        - passable_index contains passable tile coordinates.
    Usage:
        Use when a desired placement falls on unwalkable terrain.
    Parameters:
        target (Tuple[int, int]): Desired coordinate.
        passable_index (Dict[Tuple[int, int], Dict[str, object]]): Passable tiles.
        max_radius (int): Search radius limit.
    Returns:
        Tuple[int, int]: Nearest passable coordinate, or target if none found.
    Other I/O:
        None.
    """
    if target in passable_index:
        return target

    tx, ty = target
    for radius in range(1, max_radius + 1):
        for dx in range(-radius, radius + 1):
            dy_options = [radius - abs(dx), -(radius - abs(dx))]
            for dy in dy_options:
                candidate = (tx + dx, ty + dy)
                if candidate in passable_index:
                    return candidate
    # Fall back to the original target when no passable tile is nearby.
    return target


def select_start_zones(
    tiles: List[Dict[str, object]],
    max_x: int,
    max_y: int,
) -> List[Dict[str, object]]:
    """
    Description:
        Choose deterministic start zones using slope and edge distance scoring.
    Required State:
        - tiles include terrain and weather slope data.
    Usage:
        Call after computing bounds to generate start zone candidates.
    Parameters:
        tiles (List[Dict[str, object]]): Tile metadata from the payload.
        max_x (int): Maximum x coordinate in the map.
        max_y (int): Maximum y coordinate in the map.
    Returns:
        List[Dict[str, object]]: Start zone descriptors with ids and coordinates.
    Other I/O:
        None.
    """
    candidates: List[Tuple[int, int, int, int]] = []

    for tile in tiles:
        if not tile_is_passable(tile):
            continue
        try:
            x = int(tile.get("x", 0))
            y = int(tile.get("y", 0))
        except (TypeError, ValueError):
            continue
        weather = tile.get("weather") or {}
        slope = weather.get("slope", 0)
        try:
            slope_value = int(slope)
        except (TypeError, ValueError):
            slope_value = 0
        # Favor interior tiles and gentle slopes for safe starting areas.
        edge_dist = min(x, y, max_x - x, max_y - y)
        score = edge_dist * 10 - slope_value
        candidates.append((score, x, y, slope_value))

    # Sort deterministically: score desc, slope asc, then coordinate order.
    candidates.sort(key=lambda item: (-item[0], item[3], item[1], item[2]))

    max_starts = 2 if max_x >= 64 and max_y >= 64 else 1
    starts: List[Dict[str, object]] = []
    used_points: List[Tuple[int, int]] = []

    for _, x, y, slope_value in candidates:
        point = (x, y)
        # Enforce separation to avoid overlapping start zones.
        if any(manhattan(point, existing) < MIN_START_SEPARATION for existing in used_points):
            continue
        start_id = f"start_{len(starts) + 1}"
        starts.append(
            {
                "id": start_id,
                "x": x,
                "y": y,
                "slope": slope_value,
            }
        )
        used_points.append(point)
        if len(starts) >= max_starts:
            break

    return starts


def build_playable_labels(payload: Dict[str, object]) -> Dict[str, object]:
    """
    Description:
        Generate deterministic start zones and resource clusters for a payload.
    Required State:
        - payload contains a tiles list with terrain + weather.slope fields.
    Usage:
        Call after loading the payload JSON to build the playable block.
    Parameters:
        payload (Dict[str, object]): Parsed worldpayload JSON.
    Returns:
        Dict[str, object]: Playable labels block with starts and resources.
    Other I/O:
        None.
    """
    tiles = payload.get("tiles")
    if not isinstance(tiles, list):
        # Treat malformed payloads as empty to avoid crashes.
        tiles = []

    max_x, max_y = compute_bounds(tiles)
    passable_index = build_passable_index(tiles)
    starts = select_start_zones(tiles, max_x, max_y)

    resource_clusters: List[Dict[str, object]] = []
    for start in starts:
        sx = int(start["x"])
        sy = int(start["y"])

        # Fixed offsets keep resource placement deterministic and predictable.
        targets = {
            "wood": (sx + 6, sy + 4),
            "ore": (sx - 6, sy - 4),
        }

        for resource_type, (tx, ty) in targets.items():
            tx = max(0, min(max_x, tx))
            ty = max(0, min(max_y, ty))
            rx, ry = find_nearest_passable((tx, ty), passable_index, max_radius=6)
            resource_clusters.append(
                {
                    "id": f"{start['id']}_{resource_type}",
                    "type": resource_type,
                    "x": rx,
                    "y": ry,
                    "start_id": start["id"],
                }
            )

    settlement_labels: List[Dict[str, object]] = []
    for start in starts:
        settlement_labels.append(
            {
                "id": start["id"],
                "type": "start",
                "x": start["x"],
                "y": start["y"],
            }
        )

    return {
        "version": 1,
        "job_id": payload.get("job_id", "unknown"),
        "start_zones": starts,
        "resource_clusters": resource_clusters,
        "settlement_labels": settlement_labels,
        "notes": "playable labels generated from passable tiles",
    }


def write_labels(output_dir: Path, job_id: str, labels: Dict[str, object]) -> Path:
    """
    Description:
        Persist playable labels to a sidecar JSON file.
    Required State:
        - output_dir must be writable.
    Usage:
        Call after building labels to expose them to exporters.
    Parameters:
        output_dir (Path): Destination output directory.
        job_id (str): Job identifier for naming.
        labels (Dict[str, object]): Playable labels payload.
    Returns:
        Path: Path to the written sidecar JSON.
    Other I/O:
        - files: writes <job_id>.playable.json
    """
    labels_path = output_dir / f"{job_id}.playable.json"
    labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    return labels_path


def main() -> int:
    """
    Description:
        Orchestrate Playable stage execution for a single job.
    Required State:
        - input_dir must contain worldpayload artifacts.
        - output_dir and log_dir must be writable.
    Usage:
        Called by the consumer wrapper once per systemd trigger.
    Parameters:
        None: CLI arguments provide the configuration.
    Returns:
        int: Exit code (0 success, non-zero on failure).
    Other I/O:
        - files: reads worldpayload, writes augmented payload and labels
        - logs: writes logs/jobs/<job_id>/playable.log
    """
    parser = argparse.ArgumentParser(description="Playable stage processor")
    parser.add_argument("--input", dest="input_dir", required=True)
    parser.add_argument("--output", dest="output_dir", required=True)
    parser.add_argument("--log-dir", dest="log_dir", required=True)
    parser.add_argument("--job-id", dest="job_id", default=None)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)

    job = select_job(input_dir, output_dir, args.job_id)
    if not job:
        # Avoid errors when systemd triggers without new work.
        log_line(log_dir / "playable.log", "unknown", "INFO", "No new worldpayloads found")
        return 0

    log_file = log_dir / job.job_id / "playable.log"
    if job.input_path.is_dir():
        log_line(log_file, job.job_id, "INFO", f"Copying payload directory from {job.input_path}")
        try:
            copy_payload(job.input_path, job.output_path)
        except Exception as exc:
            log_line(log_file, job.job_id, "ERROR", f"Failed to copy payload: {exc}")
            return 1

        labels = {
            "version": 1,
            "job_id": job.job_id,
            "start_zones": [],
            "resource_clusters": [],
            "settlement_labels": [],
            "notes": "playable labels not generated for directory payload",
        }
        labels_path = write_labels(output_dir, job.job_id, labels)
        log_line(log_file, job.job_id, "INFO", f"Wrote labels: {labels_path}")
        return 0

    log_line(log_file, job.job_id, "INFO", f"Loading payload from {job.input_path}")

    try:
        payload = json.loads(job.input_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_line(log_file, job.job_id, "ERROR", f"Failed to read payload: {exc}")
        return 1

    labels = build_playable_labels(payload)
    payload["playable"] = labels

    try:
        job.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        log_line(log_file, job.job_id, "ERROR", f"Failed to write payload: {exc}")
        return 1

    labels_path = write_labels(output_dir, job.job_id, labels)
    log_line(log_file, job.job_id, "INFO", f"Wrote labels: {labels_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
