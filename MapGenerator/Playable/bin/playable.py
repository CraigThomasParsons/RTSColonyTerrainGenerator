#!/usr/bin/env python3
"""
Playable stage engine.

Pass-through stage that copies the latest worldpayload and emits placeholder
playability labels. This scaffolding is deterministic and safe to replace with
real placement logic.
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


PASSABLE_TERRAINS = {"grass", "rock"}
SLOPE_THRESHOLD = 6000
MIN_START_SEPARATION = 24


def log_line(log_file: Path, job_id: str, level: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{timestamp} [job={job_id}] [stage=playable] {level} {message}"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def iter_candidate_payloads(input_dir: Path) -> Iterable[Path]:
    if not input_dir.exists():
        return []
    return [path for path in input_dir.iterdir() if path.name.endswith(".worldpayload") or path.is_dir()]


def select_job(input_dir: Path, output_dir: Path, job_id: Optional[str]) -> Optional[JobSelection]:
    if job_id:
        candidate = input_dir / f"{job_id}.worldpayload"
        if candidate.exists():
            output_path = output_dir / candidate.name
            return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)
        candidate_dir = input_dir / job_id
        if candidate_dir.exists():
            output_path = output_dir / candidate_dir.name
            return JobSelection(job_id=job_id, input_path=candidate_dir, output_path=output_path)
        return None

    candidates = list(iter_candidate_payloads(input_dir))
    if not candidates:
        return None

    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        job_name = candidate.name
        job_id = job_name.replace(".worldpayload", "")
        output_path = output_dir / job_name
        if output_path.exists():
            continue
        return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)

    return None


def copy_payload(source: Path, destination: Path) -> None:
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
    max_x = 0
    max_y = 0
    for tile in tiles:
        try:
            x = int(tile.get("x", 0))
            y = int(tile.get("y", 0))
        except (TypeError, ValueError):
            continue
        if x > max_x:
            max_x = x
        if y > max_y:
            max_y = y
    return max_x, max_y


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def tile_is_passable(tile: Dict[str, object]) -> bool:
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
    index: Dict[Tuple[int, int], Dict[str, object]] = {}
    for tile in tiles:
        try:
            x = int(tile.get("x", 0))
            y = int(tile.get("y", 0))
        except (TypeError, ValueError):
            continue
        if tile_is_passable(tile):
            index[(x, y)] = tile
    return index


def find_nearest_passable(
    target: Tuple[int, int],
    passable_index: Dict[Tuple[int, int], Dict[str, object]],
    max_radius: int,
) -> Tuple[int, int]:
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
    return target


def select_start_zones(
    tiles: List[Dict[str, object]],
    max_x: int,
    max_y: int,
) -> List[Dict[str, object]]:
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
        edge_dist = min(x, y, max_x - x, max_y - y)
        score = edge_dist * 10 - slope_value
        candidates.append((score, x, y, slope_value))

    candidates.sort(key=lambda item: (-item[0], item[3], item[1], item[2]))

    max_starts = 2 if max_x >= 64 and max_y >= 64 else 1
    starts: List[Dict[str, object]] = []
    used_points: List[Tuple[int, int]] = []

    for _, x, y, slope_value in candidates:
        point = (x, y)
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
    tiles = payload.get("tiles")
    if not isinstance(tiles, list):
        tiles = []

    max_x, max_y = compute_bounds(tiles)
    passable_index = build_passable_index(tiles)
    starts = select_start_zones(tiles, max_x, max_y)

    resource_clusters: List[Dict[str, object]] = []
    for start in starts:
        sx = int(start["x"])
        sy = int(start["y"])

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
    labels_path = output_dir / f"{job_id}.playable.json"
    labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    return labels_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Playable stage scaffolding")
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
