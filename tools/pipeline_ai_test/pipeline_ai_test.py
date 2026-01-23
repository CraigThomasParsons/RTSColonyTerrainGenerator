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
        until,
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def monitor_logs(
    log_path: Path,
    duration_seconds: int,
    stale_seconds: int,
    stage_timeouts: Dict[str, int],
    repo_root: Path,
) -> int:
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

    return compute_score(state, time.time(), stale_seconds)


def parse_stage_timeout_options(stage_timeout_options: List[str]) -> Dict[str, int]:
    """Parse stage timeout overrides passed as stage=seconds.

    Why: This keeps CLI flexible without introducing config files.
    """
    defaults = {
        "heightmap": 120,
        "tiler": 120,
        "weather": 120,
        "treeplanter": 180,
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

    final_score = monitor_logs(
        log_path,
        args.duration,
        args.stale,
        stage_timeouts,
        repo_root,
    )

    if pipeline_process is not None:
        # Why: We avoid hanging if the process is still running.
        pipeline_process.terminate()

    print(f"\nFinal health score: {final_score}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
