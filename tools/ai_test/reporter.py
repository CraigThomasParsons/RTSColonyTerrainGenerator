"""Reporting system for human and machine-readable output."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class OutputFormat(Enum):
    """Supported output formats."""

    CLI = "cli"
    JSON = "json"
    YAML = "yaml"


@dataclass
class ValidationResult:
    """Result of a stage validation."""

    stage: str
    status: str  # PASS, FAIL, WARN, SKIP
    message: str = ""
    metrics: Dict[str, Any] = None
    artifacts: Dict[str, bool] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.artifacts is None:
            self.artifacts = {}


@dataclass
class PipelineReport:
    """Complete pipeline execution report."""

    job_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    health_score: int
    total_errors: int
    total_warnings: int
    stages_completed: List[str]
    stages_failed: List[str]
    issues: Dict[str, int]
    validations: List[ValidationResult]
    final_status: str  # SUCCESS, FAILURE, TIMEOUT, ABORTED

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        data = asdict(self)
        data["validations"] = [asdict(v) for v in self.validations]
        return data


class Reporter:
    """Generate human and machine-readable reports."""

    def __init__(self, output_format: OutputFormat = OutputFormat.CLI):
        self.format = output_format

    def render_live_view(
        self,
        job_id: str,
        elapsed: int,
        remaining: int,
        health_score: int,
        errors: int,
        warnings: int,
        info: int,
        stages: Dict[str, int],
        issues: Dict[str, int],
        recent_lines: List[str],
    ) -> None:
        """Render live monitoring view to terminal."""
        if self.format != OutputFormat.CLI:
            return

        # Clear screen and move cursor to top
        print("\033[2J\033[H", end="")

        # Header
        print("=" * 80)
        print("MapGenerator AI Test Framework — Live Monitor")
        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Health Score: {health_score}/100  |  Elapsed: {elapsed}s  |  Remaining: {remaining}s")
        print("-" * 80)

        # Counters
        print(f"Log Levels: INFO={info}  WARN={warnings}  ERROR={errors}")
        print()

        # Stages
        print("Stages Seen:")
        for stage, count in sorted(stages.items()):
            print(f"  • {stage}: {count} lines")
        print()

        # Issues
        if issues:
            print("Active Issues:")
            for issue, count in sorted(issues.items(), key=lambda x: -x[1])[:5]:
                print(f"  ⚠ {issue} (×{count})")
            print()

        # Recent logs
        print("-" * 80)
        print("Recent Log Lines:")
        for line in recent_lines[-12:]:
            # Truncate long lines
            if len(line) > 78:
                line = line[:75] + "..."
            print(f"  {line}")
        print("=" * 80)
        sys.stdout.flush()

    def render_report(self, report: PipelineReport) -> None:
        """Render final report in configured format."""
        if self.format == OutputFormat.CLI:
            self._render_cli_report(report)
        elif self.format == OutputFormat.JSON:
            print(json.dumps(report.to_dict(), indent=2))
        elif self.format == OutputFormat.YAML:
            if not HAS_YAML:
                print("Error: PyYAML not installed. Install with: pip install pyyaml")
                return
            print(yaml.dump(report.to_dict(), default_flow_style=False))

    def _render_cli_report(self, report: PipelineReport) -> None:
        """Render human-friendly CLI report."""
        print("\n" + "=" * 80)
        print("Pipeline Execution Report")
        print("=" * 80)
        print(f"Job ID: {report.job_id}")
        print(f"Status: {report.final_status}")
        print(f"Duration: {report.duration_seconds:.1f}s")
        print(f"Health Score: {report.health_score}/100")
        print(f"Errors: {report.total_errors}  |  Warnings: {report.total_warnings}")
        print("-" * 80)

        # Stages
        if report.stages_completed:
            print("Completed Stages:")
            for stage in report.stages_completed:
                print(f"  ✓ {stage}")

        if report.stages_failed:
            print("\nFailed Stages:")
            for stage in report.stages_failed:
                print(f"  ✗ {stage}")

        # Issues
        if report.issues:
            print("\nDetected Issues:")
            for issue, count in sorted(report.issues.items(), key=lambda x: -x[1])[:10]:
                print(f"  • {issue} (×{count})")

        # Validations
        if report.validations:
            print("\nStage Validations:")
            for val in report.validations:
                status_icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "SKIP": "○"}.get(val.status, "?")
                print(f"  {status_icon} {val.stage}: {val.status}")
                if val.message:
                    print(f"     → {val.message}")
                if val.metrics:
                    print(f"     Metrics: {val.metrics}")

        print("=" * 80)

    def export_json(self, report: PipelineReport, output_path: Path) -> None:
        """Export report as JSON file."""
        with output_path.open("w") as f:
            json.dump(report.to_dict(), f, indent=2)

    def export_yaml(self, report: PipelineReport, output_path: Path) -> None:
        """Export report as YAML file."""
        if not HAS_YAML:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
        with output_path.open("w") as f:
            yaml.dump(report.to_dict(), f, default_flow_style=False)


def create_report(
    job_id: str,
    start_time: float,
    end_time: float,
    health_score: int,
    total_errors: int,
    total_warnings: int,
    stages_completed: List[str],
    stages_failed: List[str],
    issues: Dict[str, int],
    validations: List[ValidationResult],
    final_status: str,
) -> PipelineReport:
    """Factory function to create a pipeline report."""
    return PipelineReport(
        job_id=job_id,
        start_time=datetime.fromtimestamp(start_time).isoformat(),
        end_time=datetime.fromtimestamp(end_time).isoformat(),
        duration_seconds=end_time - start_time,
        health_score=health_score,
        total_errors=total_errors,
        total_warnings=total_warnings,
        stages_completed=stages_completed,
        stages_failed=stages_failed,
        issues=issues,
        validations=validations,
        final_status=final_status,
    )
