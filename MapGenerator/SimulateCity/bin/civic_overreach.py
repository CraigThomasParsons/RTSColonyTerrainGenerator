#!/usr/bin/env python3
"""
CivicOverreach v1 - SimulateCity stage implementation.

Pure analysis + synthesis stage that reads heightmap artifacts
and emits a single worldpayload JSON describing abandoned civic
infrastructure (bridges, roads, buildings).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional


try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit(
        "Pillow is required. Install with: pip install pillow"
    ) from exc


Coord = Tuple[int, int]


@dataclass
class JobInput:
    job_id: str
    job_dir: Path
    meta_path: Path
    png_path: Path
    archive_targets: List[Path]


@dataclass
class HeightmapMeta:
    min_elevation: float
    max_elevation: float
    sea_level: float


@dataclass
class Island:
    id: int
    cells: List[Coord]
    shoreline: List[Coord]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CivicOverreach v1 generator")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--archive-dir", default=None)
    parser.add_argument("--failed-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    return parser.parse_args()


def load_meta(path: Path) -> HeightmapMeta:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return HeightmapMeta(
        min_elevation=float(payload["min_elevation"]),
        max_elevation=float(payload["max_elevation"]),
        sea_level=float(payload["sea_level"]),
    )


def find_latest_job(input_dir: Path) -> Optional[JobInput]:
    if not input_dir.exists():
        return None

    candidates: List[Tuple[float, Path]] = []

    for child in input_dir.iterdir():
        if child.is_dir():
            meta = child / "heightmap.meta.json"
            if meta.exists():
                candidates.append((meta.stat().st_mtime, meta))

    if not candidates:
        meta = input_dir / "heightmap.meta.json"
        if meta.exists():
            candidates.append((meta.stat().st_mtime, meta))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    meta_path = candidates[0][1]
    job_dir = meta_path.parent

    png_candidates = sorted(job_dir.glob("heightmap_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not png_candidates:
        return None

    png_path = png_candidates[0]

    job_id = None
    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    if isinstance(meta_payload, dict):
        job_id = meta_payload.get("job_id")

    if not job_id:
        stem = png_path.stem
        if stem.startswith("heightmap_"):
            job_id = stem.replace("heightmap_", "", 1)

    if not job_id:
        job_id = job_dir.name

    archive_targets = [meta_path] + list(job_dir.glob("heightmap_*.png"))
    return JobInput(
        job_id=job_id,
        job_dir=job_dir,
        meta_path=meta_path,
        png_path=png_path,
        archive_targets=archive_targets,
    )


def load_heightmap(png_path: Path, meta: HeightmapMeta) -> Tuple[List[List[float]], int, int]:
    image = Image.open(png_path)
    image = image.convert("I;16")
    width, height = image.size
    pixels = list(image.getdata())

    elevation_range = meta.max_elevation - meta.min_elevation
    if elevation_range <= 0:
        elevation_range = 1.0

    grid: List[List[float]] = []
    idx = 0
    for _y in range(height):
        row = []
        for _x in range(width):
            value = pixels[idx]
            idx += 1
            normalized = value / 65535.0
            elevation = meta.min_elevation + normalized * elevation_range
            row.append(elevation)
        grid.append(row)

    return grid, width, height


def neighbors(x: int, y: int, width: int, height: int) -> List[Coord]:
    results = []
    if x > 0:
        results.append((x - 1, y))
    if x < width - 1:
        results.append((x + 1, y))
    if y > 0:
        results.append((x, y - 1))
    if y < height - 1:
        results.append((x, y + 1))
    return results


def analyze_water(grid: List[List[float]], meta: HeightmapMeta, width: int, height: int) -> List[List[bool]]:
    water = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(grid[y][x] <= meta.sea_level)
        water.append(row)
    return water


def find_islands(water: List[List[bool]], width: int, height: int, min_size: int = 20) -> List[Island]:
    visited = [[False] * width for _ in range(height)]
    islands: List[Island] = []
    island_id = 0

    for y in range(height):
        for x in range(width):
            if water[y][x] or visited[y][x]:
                continue

            queue = [(x, y)]
            visited[y][x] = True
            cells: List[Coord] = []
            shoreline: List[Coord] = []

            while queue:
                cx, cy = queue.pop()
                cells.append((cx, cy))
                is_shore = False
                for nx, ny in neighbors(cx, cy, width, height):
                    if water[ny][nx]:
                        is_shore = True
                    elif not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
                if is_shore:
                    shoreline.append((cx, cy))

            if len(cells) >= min_size:
                islands.append(Island(id=island_id, cells=cells, shoreline=shoreline))
                island_id += 1

    return islands


def detect_chokepoints(water: List[List[bool]], width: int, height: int) -> List[Coord]:
    chokepoints: List[Coord] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if water[y][x]:
                continue
            north = water[y - 1][x]
            south = water[y + 1][x]
            west = water[y][x - 1]
            east = water[y][x + 1]
            if (north and south) or (west and east):
                chokepoints.append((x, y))
    return chokepoints


def find_flat_regions(
    grid: List[List[float]],
    water: List[List[bool]],
    width: int,
    height: int,
    min_size: int = 30,
) -> List[List[Coord]]:
    elevation_range = max(max(row) for row in grid) - min(min(row) for row in grid)
    threshold = max(1.0, elevation_range * 0.02)

    flat = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if water[y][x]:
                continue
            diffs = []
            for nx, ny in neighbors(x, y, width, height):
                diffs.append(abs(grid[y][x] - grid[ny][nx]))
            if diffs and max(diffs) <= threshold:
                flat[y][x] = True

    visited = [[False] * width for _ in range(height)]
    regions: List[List[Coord]] = []

    for y in range(height):
        for x in range(width):
            if not flat[y][x] or visited[y][x]:
                continue
            queue = [(x, y)]
            visited[y][x] = True
            cells: List[Coord] = []
            while queue:
                cx, cy = queue.pop()
                cells.append((cx, cy))
                for nx, ny in neighbors(cx, cy, width, height):
                    if flat[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
            if len(cells) >= min_size:
                regions.append(cells)

    return regions


def centroid(cells: List[Coord]) -> Coord:
    sx = sum(c[0] for c in cells)
    sy = sum(c[1] for c in cells)
    return int(sx / len(cells)), int(sy / len(cells))


def bresenham(a: Coord, b: Coord) -> List[Coord]:
    x0, y0 = a
    x1, y1 = b
    points: List[Coord] = []

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return points


def build_bridges(islands: List[Island], max_length: int = 20) -> List[Dict[str, object]]:
    bridges: List[Dict[str, object]] = []
    bridge_index = 1

    shoreline_samples = {
        island.id: random.sample(island.shoreline, min(len(island.shoreline), 200))
        for island in islands
    }

    for i in range(len(islands)):
        for j in range(i + 1, len(islands)):
            best: Optional[Tuple[Coord, Coord, int]] = None
            for a in shoreline_samples[islands[i].id]:
                for b in shoreline_samples[islands[j].id]:
                    if a[0] == b[0]:
                        gap = abs(a[1] - b[1])
                        if gap <= max_length and (best is None or gap < best[2]):
                            best = (a, b, gap)
                    elif a[1] == b[1]:
                        gap = abs(a[0] - b[0])
                        if gap <= max_length and (best is None or gap < best[2]):
                            best = (a, b, gap)
            if best:
                start, end, length = best
                orientation = "N-S" if start[0] == end[0] else "E-W"
                bridges.append(
                    {
                        "id": f"bridge_{bridge_index:03d}",
                        "x": min(start[0], end[0]),
                        "y": min(start[1], end[1]),
                        "length": length,
                        "orientation": orientation,
                        "status": "intact",
                        "cause": "overreach",
                    }
                )
                bridge_index += 1

    return bridges


def build_roads(flat_regions: List[List[Coord]], width: int, height: int) -> List[Dict[str, object]]:
    roads: List[Dict[str, object]] = []
    hub = (width // 2, height // 2)

    for region in flat_regions:
        region_center = centroid(region)
        path = bresenham(region_center, hub)
        roads.append({"path": path, "status": "overgrown"})

    return roads


def place_buildings(flat_regions: List[List[Coord]]) -> List[Dict[str, object]]:
    building_types = ["residential", "industrial", "commercial", "civic"]
    buildings: List[Dict[str, object]] = []

    for region in flat_regions:
        region_size = len(region)
        count = max(1, min(10, region_size // 200))
        picks = random.sample(region, min(count, len(region)))
        for cell in picks:
            buildings.append(
                {
                    "x": cell[0],
                    "y": cell[1],
                    "type": random.choice(building_types),
                    "status": "abandoned",
                }
            )

    return buildings


def near_water(point: Coord, water: List[List[bool]], radius: int = 2) -> bool:
    x, y = point
    height = len(water)
    width = len(water[0]) if height > 0 else 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if water[ny][nx]:
                    return True
    return False


def apply_disasters(
    bridges: List[Dict[str, object]],
    roads: List[Dict[str, object]],
    buildings: List[Dict[str, object]],
    water: List[List[bool]],
) -> Dict[str, List[Dict[str, object]]]:
    disaster_events: List[Dict[str, object]] = []
    maintenance_failures: List[Dict[str, object]] = []

    flooded_buildings = []
    for building in buildings:
        point = (int(building["x"]), int(building["y"]))
        if near_water(point, water, radius=3) and random.random() < 0.6:
            flooded_buildings.append(building)

    if flooded_buildings:
        disaster_events.append(
            {
                "type": "flood",
                "affected_buildings": len(flooded_buildings),
            }
        )

    for bridge in bridges:
        length = int(bridge.get("length", 0))
        if length >= 12 and random.random() < 0.7:
            bridge["status"] = "collapsed"
            bridge["cause"] = "flood"
            maintenance_failures.append(
                {"type": "bridge_collapse", "bridge_id": bridge["id"]}
            )

    for road in roads:
        if any(near_water(tuple(point), water, radius=2) for point in road["path"]):
            if random.random() < 0.5:
                road["status"] = "broken"
                maintenance_failures.append({"type": "road_failure", "reason": "flood"})

    return {
        "disaster_events": disaster_events,
        "maintenance_failures": maintenance_failures,
    }


def build_overreach_zones(islands: List[Island], chokepoints: List[Coord]) -> List[Dict[str, object]]:
    zones: List[Dict[str, object]] = []

    for island in islands:
        cx, cy = centroid(island.cells)
        zones.append(
            {
                "type": "island",
                "id": island.id,
                "centroid": [cx, cy],
                "size": len(island.cells),
            }
        )

    if chokepoints:
        samples = random.sample(chokepoints, min(len(chokepoints), 20))
        zones.append({"type": "chokepoints", "samples": samples})

    return zones


def build_payload(
    job_id: str,
    islands: List[Island],
    chokepoints: List[Coord],
    bridges: List[Dict[str, object]],
    roads: List[Dict[str, object]],
    buildings: List[Dict[str, object]],
    disasters: Dict[str, List[Dict[str, object]]],
) -> Dict[str, object]:
    payload = {
        "concrete": {
            "bridges": bridges,
            "roads": roads,
            "buildings": buildings,
        },
        "heuristics": {
            "overreach_zones": build_overreach_zones(islands, chokepoints),
            "disaster_events": disasters["disaster_events"],
            "maintenance_failures": disasters["maintenance_failures"],
        },
        "provenance": {
            "stage": "CivicOverreach",
            "version": "v1",
            "approach": "SimCity-inspired, rule-based",
            "confidence": "low",
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
    return payload


def write_output(payload: Dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


def archive_inputs(job: JobInput, archive_dir: Optional[Path]) -> None:
    if archive_dir is None:
        return
    target_dir = archive_dir / job.job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in job.archive_targets:
        if path.exists():
            path.rename(target_dir / path.name)


def fail_inputs(job: JobInput, failed_dir: Optional[Path]) -> None:
    if failed_dir is None:
        return
    target_dir = failed_dir / job.job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in job.archive_targets:
        if path.exists():
            path.rename(target_dir / path.name)


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    archive_dir = Path(args.archive_dir).expanduser().resolve() if args.archive_dir else None
    failed_dir = Path(args.failed_dir).expanduser().resolve() if args.failed_dir else None

    job = find_latest_job(input_dir)
    if job is None:
        print("[CivicOverreach] No jobs found")
        return 0

    try:
        meta = load_meta(job.meta_path)
        grid, width, height = load_heightmap(job.png_path, meta)
        water = analyze_water(grid, meta, width, height)
        islands = find_islands(water, width, height)
        chokepoints = detect_chokepoints(water, width, height)
        flat_regions = find_flat_regions(grid, water, width, height)

        bridges = build_bridges(islands)
        roads = build_roads(flat_regions, width, height)
        buildings = place_buildings(flat_regions)

        disasters = apply_disasters(bridges, roads, buildings, water)
        payload = build_payload(job.job_id, islands, chokepoints, bridges, roads, buildings, disasters)

        output_path = output_dir / f"{job.job_id}.civic_overreach.worldpayload"
        write_output(payload, output_path)
        archive_inputs(job, archive_dir)
        print(f"[CivicOverreach] Wrote {output_path}")
        return 0
    except Exception as exc:
        print(f"[CivicOverreach] Failed: {exc}")
        fail_inputs(job, failed_dir)
        return 1


if __name__ == "__main__":
    sys.exit(main())
