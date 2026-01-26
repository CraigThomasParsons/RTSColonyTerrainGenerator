#!/usr/bin/env python3
"""
WorldSnapshot engine.

Renders a WorldPreview HTML output into a PNG screenshot suitable for reports.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class JobSelection:
    job_id: str
    input_dir: Path
    output_path: Path


def log_line(log_file: Path, job_id: str, level: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{timestamp} [job={job_id}] [stage=worldsnapshot] {level} {message}"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def iter_candidate_dirs(input_dir: Path) -> Iterable[Path]:
    if not input_dir.exists():
        return []
    return [path for path in input_dir.iterdir() if path.is_dir()]


def find_job(selection_dir: Path, output_dir: Path, job_id: Optional[str]) -> Optional[JobSelection]:
    if job_id:
        explicit_dir = selection_dir / job_id
        if not explicit_dir.exists():
            return None
        output_path = output_dir / f"{job_id}.png"
        return JobSelection(job_id=job_id, input_dir=explicit_dir, output_path=output_path)

    candidates = list(iter_candidate_dirs(selection_dir))
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    for candidate in candidates:
        index_path = candidate / "index.html"
        if not index_path.exists():
            continue
        output_path = output_dir / f"{candidate.name}.png"
        if output_path.exists():
            continue
        return JobSelection(job_id=candidate.name, input_dir=candidate, output_path=output_path)

    return None


def compute_canvas_dimensions() -> str:
    return """
    () => {
        const tiles = window.WORLD_DATA?.tiles || [];
        let maxX = 0;
        let maxY = 0;
        for (const tile of tiles) {
            if (tile.x > maxX) maxX = tile.x;
            if (tile.y > maxY) maxY = tile.y;
        }
        const width = Math.max(1, (maxX + 1) * 32);
        const height = Math.max(1, (maxY + 1) * 32);
        return { width, height };
    }
    """


def normalize_camera() -> str:
    return """
    () => {
        const uiLayer = document.getElementById('ui-layer');
        if (uiLayer) {
            uiLayer.style.display = 'none';
        }
        if (typeof camera !== 'undefined') {
            camera.zoom = 1;
            camera.x = -window.innerWidth / 2;
            camera.y = -window.innerHeight / 2;
        }
        if (typeof draw === 'function') {
            draw();
        }
    }
    """


def render_snapshot(job: JobSelection, log_file: Path, timeout_seconds: int) -> int:
    index_path = job.input_dir / "index.html"
    if not index_path.exists():
        log_line(log_file, job.job_id, "ERROR", f"Missing index.html in {job.input_dir}")
        return 1

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception as exc:
        log_line(log_file, job.job_id, "ERROR", f"Playwright not available: {exc}")
        return 2

    log_line(log_file, job.job_id, "INFO", f"Rendering snapshot from {index_path}")
    timeout_ms = max(1, timeout_seconds) * 1000

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(index_path.as_uri())
            page.wait_for_selector("#world-canvas", timeout=timeout_ms)
            page.wait_for_function(
                "document.getElementById('status') && document.getElementById('status').textContent.startsWith('Loaded')",
                timeout=timeout_ms,
            )

            dimensions = page.evaluate(compute_canvas_dimensions())
            page.set_viewport_size(dimensions)
            page.evaluate(normalize_camera())
            page.wait_for_timeout(250)

            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(job.output_path), full_page=True)
            browser.close()

        log_line(log_file, job.job_id, "INFO", f"Snapshot saved to {job.output_path}")
        return 0
    except PlaywrightTimeoutError:
        log_line(log_file, job.job_id, "ERROR", "Timed out waiting for WorldPreview render")
        return 3
    except Exception as exc:
        log_line(log_file, job.job_id, "ERROR", f"Snapshot failed: {exc}")
        return 4


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a WorldPreview job into a PNG snapshot")
    parser.add_argument("--input", dest="input_dir", required=True, help="WorldPreview outbox directory")
    parser.add_argument("--output", dest="output_dir", required=True, help="WorldSnapshot outbox directory")
    parser.add_argument("--log-dir", dest="log_dir", required=True, help="Job log directory root")
    parser.add_argument("--job-id", dest="job_id", default=None, help="Specific job id to render")
    parser.add_argument("--timeout", dest="timeout", type=int, default=20, help="Render timeout in seconds")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)

    job = find_job(input_dir, output_dir, args.job_id)
    if not job:
        log_line(log_dir / "worldsnapshot.log", "unknown", "INFO", "No new WorldPreview jobs found")
        return 0

    log_file = log_dir / job.job_id / "worldsnapshot.log"
    return render_snapshot(job, log_file, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
