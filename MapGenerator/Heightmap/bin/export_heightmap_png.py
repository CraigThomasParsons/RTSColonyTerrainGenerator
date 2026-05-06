#!/usr/bin/env python3
"""Export heightmap binary to 16-bit PNG and meta JSON."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install with: pip install pillow") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export heightmap PNG + meta")
    parser.add_argument("--input", required=True, help="Path to .heightmap file")
    parser.add_argument("--output-dir", required=True, help="Target output directory")
    parser.add_argument("--job-id", default=None, help="Override job id")
    parser.add_argument("--sea-level", type=float, default=79.0, help="Sea level threshold")
    return parser.parse_args()


def read_heightmap(path: Path) -> tuple[int, int, int, list[int]]:
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError("heightmap file too small")

    width = struct.unpack_from("<I", data, 0)[0]
    height = struct.unpack_from("<I", data, 4)[0]
    seed = struct.unpack_from("<Q", data, 8)[0]

    count = width * height
    offset = 16
    if len(data) < offset + count:
        raise ValueError("heightmap file missing height bytes")

    height_bytes = list(data[offset : offset + count])
    return width, height, seed, height_bytes


def write_png(height_bytes: list[int], width: int, height: int, path: Path) -> tuple[int, int]:
    min_val = min(height_bytes) if height_bytes else 0
    max_val = max(height_bytes) if height_bytes else 0

    pixels_16 = [val * 257 for val in height_bytes]
    image = Image.new("I;16", (width, height))
    image.putdata(pixels_16)
    image.save(path)

    return min_val, max_val


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = args.job_id or input_path.stem

    width, height, seed, height_bytes = read_heightmap(input_path)
    png_path = output_dir / f"heightmap_{job_id}.png"
    min_val, max_val = write_png(height_bytes, width, height, png_path)

    meta = {
        "job_id": job_id,
        "width": width,
        "height": height,
        "seed": seed,
        "min_elevation": float(min_val),
        "max_elevation": float(max_val),
        "sea_level": float(args.sea_level),
    }

    meta_path = output_dir / "heightmap.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
