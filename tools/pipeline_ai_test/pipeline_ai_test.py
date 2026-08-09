#!/usr/bin/env python3
"""
AI-driven pipeline tester for MapGenerator.

This tool launches a pipeline run (optional) and monitors logs in real time.
It uses heuristic signals to score health and surface likely issues.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG_LINE_PATTERN = re.compile(
    r"^(?P<ts>\S+) \[job=(?P<job>[^\]]+)\] \[stage=(?P<stage>[^\]]+)\] (?P<level>\S+) (?P<msg>.*)$"
)


@dataclass
class HealthState:
    job_id: str = "unknown"
    last_line_at: float = 0.0
    last_stage_at: Dict[str, float] = field(default_factory=dict)
    stage_seen: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    warn_count: int = 0
    info_count: int = 0
    issues: Dict[str, int] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

    def record_line(self, line: str, now: float) -> None:
        """Track line stats for scoring and display.

        Why: Centralizing updates keeps scoring logic consistent.
        """
        self.last_line_at = now
        self.raw_lines.append(line)
        if len(self.raw_lines) > 50:
            self.raw_lines.pop(0)


def parse_log_line(line: str) -> Optional[Dict[str, str]]:
    """Parse a normalized log line into fields.

    Why: The tester needs stage/job/level to score health.
    """
    match = LOG_LINE_PATTERN.match(line)
    if not match:
        return None
    return match.groupdict()


def render_screen(state: HealthState, score: int, duration_seconds: int, start_time: float) -> None:
    """Render a simple live view to the terminal.

    Why: A live view helps debug stalls without switching tools.
    """
    elapsed = int(time.time() - start_time)
    remaining = max(0, duration_seconds - elapsed)

    print("\033[2J\033[H", end="")
    print("MapGenerator Pipeline AI Test")
    print(f"Job: {state.job_id}  |  Score: {score}  |  Elapsed: {elapsed}s  |  Remaining: {remaining}s")
    print("-" * 80)
    print(f"INFO: {state.info_count}  WARN: {state.warn_count}  ERROR: {state.error_count}")
    print("Stages seen:")
    for stage, count in sorted(state.stage_seen.items()):
        print(f"  - {stage}: {count}")
    print("Active issues:")
    for issue, count in sorted(state.issues.items()):
        print(f"  - {issue} (x{count})")
    print("-" * 80)
    print("Recent log lines:")
    for line in state.raw_lines[-12:]:
        print(line)


def compute_score(state: HealthState, now: float, stale_seconds: int) -> int:
    """Compute a simple health score from log activity.

    Why: A numeric score makes regressions easy to spot.
    """
    score = 100
    score -= state.error_count * 15
    score -= state.warn_count * 5

    if state.last_line_at > 0 and now - state.last_line_at > stale_seconds:
        score -= 20

    issue_penalty = sum(state.issues.values()) * 3
    score -= issue_penalty

    return max(0, score)


def record_issue(state: HealthState, issue_key: str) -> None:
    """Record a detected issue and increment its count.

    Why: Aggregating issues allows the tester to highlight recurring failures.
    """
    state.issues[issue_key] = state.issues.get(issue_key, 0) + 1


def detect_issue_from_line(state: HealthState, message: str) -> None:
    """Detect known failure patterns and record suggested fixes.

    Why: Triage hints reduce time spent scanning logs manually.
    """
    issue_patterns: List[Tuple[str, str]] = [
        (
            "Failed to parse maptiles",
            "Maptiles parse failed → verify binary MTIL support and Tiler output integrity",
        ),
        (
            "Failed to parse weather",
            "Weather parse failed → verify WeatherAnalyses binary format and file completeness",
        ),
        (
            "Tile count mismatch",
            "Tile count mismatch → check cell vs tile dimension mapping (2x resolution)",
        ),
        (
            "Class \"MapGenerator\\TreePlanter\\Engine\\TreePlacementEngine\" not found",
            "Autoload error → verify PSR-4 filename for TreePlacementEngine",
        ),
        (
            "Invalid numeric literal",
            "Non-JSON log line parsed as JSON → confirm LogStreamer text normalization",
        ),
        (
            "stratagus harness failed",
            "Stratagus harness failed → verify SCM output and harness.lua compatibility",
        ),
        (
            "HARNESS:FAIL",
            "Stratagus reported HARNESS:FAIL → inspect stratagus_stdout.log for details",
        ),
    ]

    for snippet, suggestion in issue_patterns:
        if snippet in message:
            record_issue(state, suggestion)


def build_stage_artifact_map(repo_root: Path, job_id: str) -> Dict[str, Path]:
    """Return authoritative artifact paths for each stage.

    Why: Artifact presence is the source of truth for stage completion.
    """
    return {
        "heightmap": repo_root / "MapGenerator" / "Heightmap" / "outbox" / f"{job_id}.heightmap",
        "tiler": repo_root / "MapGenerator" / "Tiler" / "outbox" / f"{job_id}.maptiles",
        "weather": repo_root / "MapGenerator" / "WeatherAnalyses" / "outbox" / f"{job_id}.weather",
        "treeplanter": repo_root / "MapGenerator" / "TreePlanter" / "outbox" / f"{job_id}.worldpayload",
        "cartridge": repo_root / "MapGenerator" / "CartridgeManufacturer" / "outbox" / f"{job_id}.wcar",
    }


def detect_stage_timeouts(
    state: HealthState,
    repo_root: Path,
    stage_timeouts: Dict[str, int],
    now: float,
) -> None:
    """Detect stages that appear stalled beyond expected timeouts.

    Why: Stages can hang silently; timeouts surface likely stalls.
    """
    if state.job_id == "unknown":
        return

    artifact_map = build_stage_artifact_map(repo_root, state.job_id)

    for stage, timeout_seconds in stage_timeouts.items():
        last_seen = state.last_stage_at.get(stage)
        artifact_path = artifact_map.get(stage)

        if last_seen is None:
            continue

        if artifact_path is not None and artifact_path.exists():
            continue

        if now - last_seen > timeout_seconds:
            record_issue(
                state,
                f"Stage timeout: {stage} (> {timeout_seconds}s) → check worker/service and artifacts",
            )


def run_pipeline(width: int, height: int, until: str) -> subprocess.Popen:
    """Start a pipeline run using mapgenctl.

    Why: The tester should be able to orchestrate a run end-to-end.
    """
    until_arg = normalize_until(until)
    command = [
        sys.executable,
        "-m",
        "tools.mapgenctl",
        "run",
        "--width",
        str(width),
        "--height",
        str(height),
        "--until",
        until_arg,
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def normalize_until(until: str) -> str:
    """Map requested stage names to valid mapgenctl values.

    Why: mapgenctl only supports core stages, while follow-on stages
    are handled by systemd consumers.
    """
    valid_until = {"heightmap", "tiler", "weather", "treeplanter"}
    if until in valid_until:
        return until
    if until in {"worldfeatures", "pathfinder", "worldpreview", "cartridge"}:
        return "treeplanter"
    return until


def monitor_logs(
    log_path: Path,
    duration_seconds: int,
    stale_seconds: int,
    stage_timeouts: Dict[str, int],
    repo_root: Path,
    render: bool,
) -> Tuple[int, str]:
    """Tail the main log file and evaluate health.

    Why: The global log is the authoritative stream across stages.
    """
    state = HealthState()
    start_time = time.time()

    with log_path.open("r", encoding="utf-8", errors="replace") as log_file:
        log_file.seek(0, os.SEEK_END)

        while True:
            now = time.time()
            if now - start_time > duration_seconds:
                break

            line = log_file.readline()
            if not line:
                score = compute_score(state, now, stale_seconds)
                if render:
                    render_screen(state, score, duration_seconds, start_time)
                time.sleep(0.5)
                continue

            line = line.rstrip("\n")
            if not line:
                continue

            parsed = parse_log_line(line)
            if parsed:
                state.job_id = parsed.get("job", state.job_id)
                stage = parsed.get("stage", "unknown")
                level = parsed.get("level", "INFO").upper()
                message = parsed.get("msg", "")

                state.stage_seen[stage] = state.stage_seen.get(stage, 0) + 1
                state.last_stage_at[stage] = now

                if level == "ERROR":
                    state.error_count += 1
                elif level == "WARN":
                    state.warn_count += 1
                else:
                    state.info_count += 1

                detect_issue_from_line(state, message)

            state.record_line(line, now)

            # Why: Periodically check for stage stalls without flooding the UI.
            detect_stage_timeouts(state, repo_root, stage_timeouts, now)

    return compute_score(state, time.time(), stale_seconds), state.job_id


def infer_latest_job_id(repo_root: Path) -> Optional[str]:
    """Infer the latest job id from logs or outbox artifacts.

    Why: Tests should still run if log aggregation is down.
    """
    logs_root = repo_root / "logs" / "jobs"
    if logs_root.exists():
        job_dirs = [p for p in logs_root.iterdir() if p.is_dir()]
        if job_dirs:
            job_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return job_dirs[0].name

    inferred = infer_latest_worldpreview_job_id(repo_root)
    if inferred:
        return inferred

    inferred = infer_latest_worldsnapshot_job_id(repo_root)
    if inferred:
        return inferred

    stargus_outbox = repo_root / "MapGenerator" / "StargusExport" / "outbox"
    if stargus_outbox.exists():
        inferred = infer_latest_stargus_job_id(repo_root)
        if inferred:
            return inferred

    cartridge_outbox = repo_root / "MapGenerator" / "CartridgeManufacturer" / "outbox"
    if cartridge_outbox.exists():
        candidates = list(cartridge_outbox.glob("*.wcar"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0].stem

    treeplanter_outbox = repo_root / "MapGenerator" / "TreePlanter" / "outbox"
    if treeplanter_outbox.exists():
        candidates = list(treeplanter_outbox.glob("*.worldpayload"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0].stem

    playable_outbox = repo_root / "MapGenerator" / "Playable" / "outbox"
    if playable_outbox.exists():
        candidates = list(playable_outbox.glob("*.worldpayload"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0].stem

    return None


def infer_latest_worldpreview_job_id(repo_root: Path) -> Optional[str]:
    """Return the latest job id that has a WorldPreview index.html."""
    outbox = repo_root / "MapGenerator" / "WorldPreview" / "outbox"
    if not outbox.exists():
        return None
    candidates = list(outbox.glob("*/index.html"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].parent.name


def infer_latest_worldsnapshot_job_id(repo_root: Path) -> Optional[str]:
    """Return the latest job id that has a WorldSnapshot PNG."""
    outbox = repo_root / "MapGenerator" / "WorldSnapshot" / "outbox"
    if not outbox.exists():
        return None
    candidates = list(outbox.glob("*.png"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].stem


def infer_latest_stargus_job_id(repo_root: Path) -> Optional[str]:
    """Return the latest job id that has both CHK and SCM outputs."""
    outbox = repo_root / "MapGenerator" / "StargusExport" / "outbox"
    if not outbox.exists():
        return None
    chk_files = {p.stem: p for p in outbox.glob("*.chk")}
    scm_files = {p.stem: p for p in outbox.glob("*.scm")}
    shared = set(chk_files.keys()) & set(scm_files.keys())
    if not shared:
        return None
    candidates = [(stem, max(chk_files[stem].stat().st_mtime, scm_files[stem].stat().st_mtime)) for stem in shared]
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def run_worldpreview_playwright(repo_root: Path, job_id: str, timeout_seconds: int) -> Tuple[bool, str]:
    """Open WorldPreview output using Playwright and perform basic UI checks.

    Why: Validates the final stage renders correctly for human inspection.
    """
    if job_id == "unknown":
        inferred = infer_latest_worldpreview_job_id(repo_root)
        if not inferred:
            return False, "No job_id detected from logs"
        job_id = inferred

    preview_path = repo_root / "MapGenerator" / "WorldPreview" / "outbox" / job_id / "index.html"
    if not preview_path.exists():
        return False, f"WorldPreview index not found: {preview_path}"

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception as exc:
        return False, f"Playwright not available: {exc} (install: pip install playwright && playwright install)"

    url = preview_path.as_uri()
    timeout_ms = max(1, timeout_seconds) * 1000

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            page.wait_for_selector("#world-canvas", timeout=timeout_ms)
            page.wait_for_selector("#toggle-height", timeout=timeout_ms)
            page.wait_for_selector("#toggle-terrain", timeout=timeout_ms)
            page.wait_for_selector("#toggle-features", timeout=timeout_ms)
            page.wait_for_selector("#toggle-paths", timeout=timeout_ms)

            # Ensure canvas has dimensions
            canvas_box = page.locator("#world-canvas").bounding_box()
            if not canvas_box or canvas_box["width"] <= 0 or canvas_box["height"] <= 0:
                browser.close()
                return False, "Canvas has invalid dimensions"

            # Trigger hover update
            page.mouse.move(canvas_box["x"] + 10, canvas_box["y"] + 10)
            page.wait_for_timeout(500)
            hover_text = page.locator("#hover-info").text_content() or ""

            browser.close()

            if "Hover over a tile" in hover_text:
                return False, "Hover inspector did not update"

            return True, "WorldPreview rendered successfully"

    except PlaywrightTimeoutError:
        return False, "WorldPreview UI did not load within timeout"
    except Exception as exc:
        return False, f"WorldPreview Playwright check failed: {exc}"


def wait_for_worldsnapshot(repo_root: Path, job_id: str, timeout_seconds: int) -> Tuple[bool, str]:
    """Wait for WorldSnapshot output to appear for a job.

    Why: WorldSnapshot is asynchronous and may lag behind WorldPreview output.
    """
    if job_id == "unknown":
        inferred = infer_latest_worldpreview_job_id(repo_root)
        if inferred:
            job_id = inferred
        else:
            return False, "No job_id detected from logs"

    snapshot_path = repo_root / "MapGenerator" / "WorldSnapshot" / "outbox" / f"{job_id}.png"
    deadline = time.time() + max(1, timeout_seconds)

    while time.time() < deadline:
        if snapshot_path.exists():
            return True, f"WorldSnapshot found: {snapshot_path}"
        time.sleep(0.5)

    return False, f"WorldSnapshot not found within {timeout_seconds}s: {snapshot_path}"


def run_worldsnapshot_consumer(repo_root: Path, timeout_seconds: int) -> Tuple[bool, str]:
    """Run the WorldSnapshot consumer script.

    Why: WorldSnapshot is triggered by a consumer, not mapgenctl.
    """
    script = repo_root / "MapGenerator" / "WorldSnapshot" / "bin" / "consume_worldsnapshot_job.sh"
    if not script.exists():
        return False, f"WorldSnapshot consumer not found: {script}"

    try:
        result = subprocess.run([str(script)], check=False, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return False, f"WorldSnapshot consumer timed out after {timeout_seconds}s"

    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = stderr if stderr else f"exit code {result.returncode}"
        return False, f"WorldSnapshot consumer failed: {detail}"

    return True, "WorldSnapshot consumer completed"


def wait_for_stargus_export(repo_root: Path, job_id: str, timeout_seconds: int) -> Tuple[bool, str]:
    """Wait for StargusExport outputs to appear for a job.

    Why: StargusExport is a key artifact path for CHK/SCM validation.
    """
    outbox = repo_root / "MapGenerator" / "StargusExport" / "outbox"
    deadline = time.time() + max(1, timeout_seconds)

    while time.time() < deadline:
        if job_id != "unknown":
            chk_path = outbox / f"{job_id}.chk"
            scm_path = outbox / f"{job_id}.scm"
            if chk_path.exists() and scm_path.exists():
                ok, detail = validate_chk_mtxm(chk_path)
                if not ok:
                    return False, detail
                return True, f"StargusExport outputs found: {chk_path}, {scm_path}"
        else:
            inferred = infer_latest_stargus_job_id(repo_root)
            if inferred:
                chk_path = outbox / f"{inferred}.chk"
                scm_path = outbox / f"{inferred}.scm"
                if chk_path.exists() and scm_path.exists():
                    ok, detail = validate_chk_mtxm(chk_path)
                    if not ok:
                        return False, detail
                    return True, f"StargusExport outputs found: {chk_path}, {scm_path}"
        time.sleep(0.5)

    if job_id == "unknown":
        return False, f"StargusExport outputs not found within {timeout_seconds}s"
    return False, f"StargusExport outputs not found within {timeout_seconds}s: {chk_path}, {scm_path}"


def parse_chk_sections(data: bytes) -> Dict[str, bytes]:
    offset = 0
    sections: Dict[str, bytes] = {}
    length = len(data)

    while offset + 8 <= length:
        name = data[offset : offset + 4].decode("ascii", errors="replace").rstrip()
        size = struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
        if offset + size > length:
            break
        sections[name] = data[offset : offset + size]
        offset += size

    return sections


def validate_chk_mtxm(chk_path: Path) -> Tuple[bool, str]:
    try:
        data = chk_path.read_bytes()
    except Exception as exc:
        return False, f"Failed to read CHK: {chk_path} ({exc})"

    sections = parse_chk_sections(data)
    if "DIM" not in sections or "MTXM" not in sections:
        return False, f"CHK missing DIM/MTXM: {chk_path}"

    width, height = struct.unpack_from("<HH", sections["DIM"], 0)
    count = int(width * height)
    mtxm = sections["MTXM"]
    if len(mtxm) < count * 2:
        return False, f"MTXM too short for DIM ({width}x{height}) in {chk_path}"

    tile_ids = struct.unpack_from(f"<{count}H", mtxm, 0)
    unique_tiles = len(set(tile_ids))
    if unique_tiles <= 1:
        return False, (
            f"MTXM is uniform ({unique_tiles} unique tile). "
            f"Check StargusExport tileset mapping (likely all 0s)."
        )

    return True, f"MTXM OK ({unique_tiles} unique tiles)"


def run_stargus_consumer(repo_root: Path, timeout_seconds: int) -> Tuple[bool, str]:
    """Run the StargusExport consumer script.

    Why: StargusExport is triggered by a consumer, not mapgenctl.
    """
    script = repo_root / "MapGenerator" / "StargusExport" / "bin" / "consume_stargusexport_job.sh"
    if not script.exists():
        return False, f"StargusExport consumer not found: {script}"

    try:
        result = subprocess.run([str(script)], check=False, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return False, f"StargusExport consumer timed out after {timeout_seconds}s"

    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = stderr if stderr else f"exit code {result.returncode}"
        return False, f"StargusExport consumer failed: {detail}"

    return True, "StargusExport consumer completed"


def parse_stage_timeout_options(stage_timeout_options: List[str]) -> Dict[str, int]:
    """Parse stage timeout overrides passed as stage=seconds.

    Why: This keeps CLI flexible without introducing config files.
    """
    defaults = {
        "heightmap": 120,
        "tiler": 120,
        "weather": 120,
        "treeplanter": 180,
        "cartridge": 120,
    }

    for option in stage_timeout_options:
        if "=" not in option:
            continue
        stage_name, seconds_text = option.split("=", 1)
        if not seconds_text.isdigit():
            continue
        defaults[stage_name.strip()] = int(seconds_text)

    return defaults


def main() -> int:
    parser = argparse.ArgumentParser(description="AI-driven pipeline tester for MapGenerator.")
    parser.add_argument("--width", type=int, default=64, help="Map width in cells")
    parser.add_argument("--height", type=int, default=64, help="Map height in cells")
    parser.add_argument("--until", type=str, default="treeplanter", help="Pipeline stop stage")
    parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    parser.add_argument("--stale", type=int, default=12, help="Seconds without logs before penalizing score")
    parser.add_argument(
        "--stage-timeout",
        action="append",
        default=[],
        help="Override stage timeout (format: stage=seconds). Can be repeated.",
    )
    parser.add_argument("--follow-only", action="store_true", help="Only tail logs; do not start a job")
    parser.add_argument("--log", type=str, default="logs/mapgen.log", help="Path to log file")
    parser.add_argument(
        "--playwright-worldpreview",
        action="store_true",
        help="After monitoring, open WorldPreview output via Playwright and validate UI",
    )
    parser.add_argument(
        "--playwright-timeout",
        type=int,
        default=15,
        help="Timeout in seconds for Playwright UI checks",
    )
    parser.add_argument(
        "--worldsnapshot",
        action="store_true",
        help="After monitoring, wait for WorldSnapshot PNG output",
    )
    parser.add_argument(
        "--worldsnapshot-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for WorldSnapshot output",
    )
    parser.add_argument(
        "--run-worldsnapshot-consumer",
        action="store_true",
        help="Run the WorldSnapshot consumer before checking output",
    )
    parser.add_argument(
        "--worldsnapshot-consumer-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for the WorldSnapshot consumer script",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Disable live screen rendering (useful for CI or long runs)",
    )
    parser.add_argument(
        "--stargus-export",
        action="store_true",
        help="After monitoring, wait for StargusExport CHK/SCM outputs",
    )
    parser.add_argument(
        "--stargus-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for StargusExport outputs",
    )
    parser.add_argument(
        "--run-stargus-consumer",
        action="store_true",
        help="Run the StargusExport consumer before checking outputs",
    )
    parser.add_argument(
        "--stargus-consumer-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for the StargusExport consumer script",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return 1

    pipeline_process: Optional[subprocess.Popen] = None
    if not args.follow_only:
        # Why: Spawning a job ensures the tester can be used standalone.
        pipeline_process = run_pipeline(args.width, args.height, args.until)

    repo_root = Path(__file__).resolve().parents[2]
    stage_timeouts = parse_stage_timeout_options(args.stage_timeout)

    final_score, job_id = monitor_logs(
        log_path,
        args.duration,
        args.stale,
        stage_timeouts,
        repo_root,
        render=not args.no_render,
    )

    if pipeline_process is not None:
        # Why: We avoid hanging if the process is still running.
        pipeline_process.terminate()

    if job_id == "unknown":
        inferred = infer_latest_job_id(repo_root)
        if inferred:
            job_id = inferred
            print(f"\nNo job_id from logs; inferred latest job: {job_id}")

    print(f"\nFinal health score: {final_score}")

    if args.playwright_worldpreview:
        ok, message = run_worldpreview_playwright(repo_root, job_id, args.playwright_timeout)
        status = "PASS" if ok else "FAIL"
        print(f"WorldPreview Playwright: {status} - {message}")
        if not ok:
            return 2

    if args.worldsnapshot:
        if args.run_worldsnapshot_consumer:
            ok, message = run_worldsnapshot_consumer(repo_root, args.worldsnapshot_consumer_timeout)
            status = "PASS" if ok else "FAIL"
            print(f"WorldSnapshot consumer: {status} - {message}")
            if not ok:
                return 3
        ok, message = wait_for_worldsnapshot(repo_root, job_id, args.worldsnapshot_timeout)
        status = "PASS" if ok else "FAIL"
        print(f"WorldSnapshot: {status} - {message}")
        if not ok:
            return 3

    if args.stargus_export:
        if args.run_stargus_consumer:
            ok, message = run_stargus_consumer(repo_root, args.stargus_consumer_timeout)
            status = "PASS" if ok else "FAIL"
            print(f"StargusExport consumer: {status} - {message}")
            if not ok:
                return 4
        ok, message = wait_for_stargus_export(repo_root, job_id, args.stargus_timeout)
        status = "PASS" if ok else "FAIL"
        print(f"StargusExport: {status} - {message}")
        if not ok:
            return 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
