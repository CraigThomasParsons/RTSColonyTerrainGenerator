#!/usr/bin/env python3
"""Smoke test for CivicOverreach v1 stage."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


def build_heightmap(path: Path, width: int, height: int) -> None:
    pixels = []
    for y in range(height):
        for x in range(width):
            value = int((x + y) / (width + height - 2) * 65535)
            pixels.append(value)

    image = Image.new("I;16", (width, height))
    image.putdata(pixels)
    image.save(path)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_dir = root / "input"
        output_dir = root / "output"
        archive_dir = root / "archive"
        failed_dir = root / "failed"
        log_dir = root / "logs"

        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        job_id = "smoke-job"
        meta_path = input_dir / "heightmap.meta.json"
        png_path = input_dir / f"heightmap_{job_id}.png"

        meta_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "min_elevation": 0,
                    "max_elevation": 100,
                    "sea_level": 30,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        build_heightmap(png_path, 64, 64)

        stage_script = (
            Path(__file__).resolve().parents[1] / "bin" / "civic_overreach.py"
        )

        result = subprocess.run(
            [
                sys.executable,
                str(stage_script),
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--archive-dir",
                str(archive_dir),
                "--failed-dir",
                str(failed_dir),
                "--log-dir",
                str(log_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Stage failed: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        output_file = output_dir / f"{job_id}.civic_overreach.worldpayload"
        if not output_file.exists():
            raise FileNotFoundError(f"Missing output: {output_file}")

        payload = json.loads(output_file.read_text(encoding="utf-8"))
        for key in ("concrete", "heuristics", "provenance"):
            if key not in payload:
                raise ValueError(f"Missing top-level key: {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
