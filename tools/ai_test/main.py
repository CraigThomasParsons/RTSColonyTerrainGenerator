#!/usr/bin/env python3
"""AI-driven pipeline test framework main entry point.

Usage examples:
  # Monitor live pipeline with default settings
  python -m tools.ai_test

  # Start a new pipeline and monitor it
  python -m tools.ai_test --run --width 128 --height 128

  # Verify specific stage for existing job
  python -m tools.ai_test --verify-stage PathFinder --job-id <uuid>

  # Export results as JSON
  python -m tools.ai_test --run --json-output --export report.json
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from .controller import PipelineConfig, PipelineController
from .registry import StageRegistry
from .reporter import OutputFormat, Reporter, create_report
from .sentinel import LogSentinel
from .validators import ValidatorFactory


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).resolve().parents[2]


def monitor_pipeline(
    args: argparse.Namespace,
    registry: StageRegistry,
    reporter: Reporter,
) -> int:
    """Monitor a running pipeline with live updates."""
    log_path = get_repo_root() / args.log

    # Optional: start new pipeline run
    controller = None
    if args.run:
        config = PipelineConfig(
            width=args.width,
            height=args.height,
            until_stage=args.until,
            repo_root=get_repo_root(),
        )
        controller = PipelineController(config)
        if not controller.start():
            print("Failed to start pipeline")
            return 1
        print(f"Started pipeline: {args.width}x{args.height} until {args.until}")
        time.sleep(2)  # Give it time to start logging

    # Initialize sentinel
    sentinel = LogSentinel(log_path)
    try:
        sentinel.start()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        if controller:
            controller.stop()
        return 1

    start_time = time.time()
    end_time = start_time + args.duration

    # Build stage timeout map
    stage_timeouts = {}
    for stage in registry.all_stages():
        stage_timeouts[stage.name.lower()] = stage.timeout_seconds

    # Override with CLI args
    for override in args.stage_timeout:
        if "=" not in override:
            continue
        stage, timeout_str = override.split("=", 1)
        if timeout_str.isdigit():
            stage_timeouts[stage.strip().lower()] = int(timeout_str)

    # Monitoring loop
    try:
        while time.time() < end_time:
            entries = sentinel.poll()

            now = time.time()
            elapsed = int(now - start_time)
            remaining = int(end_time - now)

            health_score = sentinel.compute_health_score(args.stale)
            stalled = sentinel.detect_stalled_stages(stage_timeouts)

            # Update stalled stages in issues
            for stall_msg in stalled:
                sentinel.state.issues[f"Stalled: {stall_msg}"] = 1

            # Render live view (CLI only)
            if reporter.format == OutputFormat.CLI:
                reporter.render_live_view(
                    job_id=sentinel.state.job_id,
                    elapsed=elapsed,
                    remaining=remaining,
                    health_score=health_score,
                    errors=sentinel.state.total_errors,
                    warnings=sentinel.state.total_warnings,
                    info=sentinel.state.total_info,
                    stages={s.name: s.line_count for s in sentinel.state.stages.values()},
                    issues=sentinel.state.issues,
                    recent_lines=sentinel.state.recent_lines,
                )

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")

    finally:
        sentinel.stop()
        if controller:
            controller.stop()

    # Generate final report
    final_time = time.time()
    health_score = sentinel.compute_health_score(args.stale)

    stages_completed = [s.name for s in sentinel.state.stages.values() if s.line_count > 0]
    stages_failed = []

    # Run validations if we have a job ID
    validations = []
    if sentinel.state.job_id != "unknown":
        validator_factory = ValidatorFactory(registry)
        validations = validator_factory.validate_all(sentinel.state.job_id, stages_completed)

        # Mark failed stages
        for val in validations:
            if val.status == "FAIL":
                stages_failed.append(val.stage)

    # Determine final status
    if sentinel.state.total_errors > 0:
        final_status = "FAILURE"
    elif stages_failed:
        final_status = "FAILURE"
    elif health_score < 50:
        final_status = "DEGRADED"
    else:
        final_status = "SUCCESS"

    report = create_report(
        job_id=sentinel.state.job_id,
        start_time=start_time,
        end_time=final_time,
        health_score=health_score,
        total_errors=sentinel.state.total_errors,
        total_warnings=sentinel.state.total_warnings,
        stages_completed=stages_completed,
        stages_failed=stages_failed,
        issues=sentinel.state.issues,
        validations=validations,
        final_status=final_status,
    )

    reporter.render_report(report)

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        if args.json_output:
            reporter.export_json(report, export_path)
        else:
            reporter.export_yaml(report, export_path)
        print(f"\nReport exported to {export_path}")

    return 0 if final_status == "SUCCESS" else 1


def verify_stage(
    args: argparse.Namespace,
    registry: StageRegistry,
    reporter: Reporter,
) -> int:
    """Verify a specific stage for a given job ID."""
    if not args.job_id:
        print("Error: --job-id required for --verify-stage")
        return 1

    validator_factory = ValidatorFactory(registry)
    validator = validator_factory.create(args.verify_stage)
    result = validator.validate(args.job_id)

    if reporter.format == OutputFormat.JSON:
        import json
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"\nStage Validation: {args.verify_stage}")
        print(f"Job ID: {args.job_id}")
        print(f"Status: {result.status}")
        print(f"Message: {result.message}")
        if result.metrics:
            print(f"Metrics: {result.metrics}")
        if result.artifacts:
            print("Artifacts:")
            for name, exists in result.artifacts.items():
                status = "✓" if exists else "✗"
                print(f"  {status} {name}")

    return 0 if result.status == "PASS" else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI-driven pipeline test framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Execution modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--run", action="store_true", help="Start a new pipeline run")
    mode_group.add_argument("--verify-stage", type=str, help="Verify specific stage (requires --job-id)")

    # Pipeline configuration
    parser.add_argument("--width", type=int, default=64, help="Map width in cells (default: 64)")
    parser.add_argument("--height", type=int, default=64, help="Map height in cells (default: 64)")
    parser.add_argument("--until", type=str, default="WorldPreview", help="Stop at this stage (default: WorldPreview)")

    # Monitoring configuration
    parser.add_argument("--duration", type=int, default=120, help="Monitoring duration in seconds (default: 120)")
    parser.add_argument("--stale", type=int, default=15, help="Seconds without logs before penalty (default: 15)")
    parser.add_argument(
        "--stage-timeout",
        action="append",
        default=[],
        help="Override stage timeout (format: stage=seconds). Can be repeated.",
    )
    parser.add_argument("--log", type=str, default="logs/mapgen.log", help="Path to log file (default: logs/mapgen.log)")

    # Output configuration
    parser.add_argument("--json-output", action="store_true", help="Output in JSON format")
    parser.add_argument("--yaml-output", action="store_true", help="Output in YAML format")
    parser.add_argument("--export", type=str, help="Export report to file")

    # Validation
    parser.add_argument("--job-id", type=str, help="Job ID for validation")

    args = parser.parse_args()

    # Determine output format
    if args.json_output:
        output_format = OutputFormat.JSON
    elif args.yaml_output:
        output_format = OutputFormat.YAML
    else:
        output_format = OutputFormat.CLI

    # Initialize components
    repo_root = get_repo_root()
    registry = StageRegistry(repo_root)
    reporter = Reporter(output_format)

    # Route to appropriate handler
    if args.verify_stage:
        return verify_stage(args, registry, reporter)
    else:
        return monitor_pipeline(args, registry, reporter)


if __name__ == "__main__":
    sys.exit(main())
