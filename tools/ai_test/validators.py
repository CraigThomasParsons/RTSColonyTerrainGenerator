"""Stage validation system with pluggable validators."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from .registry import StageRegistry
from .reporter import ValidationResult


class Validator(ABC):
    """Base class for stage validators."""

    def __init__(self, stage_name: str, registry: StageRegistry):
        self.stage_name = stage_name
        self.registry = registry

    @abstractmethod
    def validate(self, job_id: str) -> ValidationResult:
        """Validate stage artifacts and return result."""
        pass

    def _check_artifacts(self, job_id: str) -> Dict[str, bool]:
        """Check which artifacts exist for this stage."""
        return self.registry.check_artifacts(self.stage_name, job_id)


class GenericValidator(Validator):
    """Generic validator that checks for artifact presence."""

    def validate(self, job_id: str) -> ValidationResult:
        artifacts = self._check_artifacts(job_id)

        if not artifacts:
            return ValidationResult(
                stage=self.stage_name,
                status="SKIP",
                message="No artifacts defined for stage",
            )

        all_exist = all(artifacts.values())
        missing = [k for k, v in artifacts.items() if not v]

        if all_exist:
            return ValidationResult(
                stage=self.stage_name,
                status="PASS",
                message=f"All {len(artifacts)} artifacts present",
                artifacts=artifacts,
            )
        else:
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message=f"Missing artifacts: {', '.join(missing)}",
                artifacts=artifacts,
            )


class HeightmapValidator(Validator):
    """Validator for Heightmap stage."""

    def validate(self, job_id: str) -> ValidationResult:
        artifacts = self._check_artifacts(job_id)

        if not any(artifacts.values()):
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message="Heightmap artifact not found",
                artifacts=artifacts,
            )

        # Get heightmap path
        stage_def = self.registry.get(self.stage_name)
        heightmap_path = stage_def.artifact_path(
            self.registry.repo_root, job_id, "{job_id}.heightmap"
        )

        try:
            # Check for flat map (all same value)
            with open(heightmap_path, "rb") as f:
                data = f.read()
                if len(data) < 100:
                    return ValidationResult(
                        stage=self.stage_name,
                        status="FAIL",
                        message=f"Heightmap too small ({len(data)} bytes)",
                        artifacts=artifacts,
                    )

                # Sample first 100 values
                sample = data[:100]
                if len(set(sample)) < 3:
                    return ValidationResult(
                        stage=self.stage_name,
                        status="WARN",
                        message="Heightmap appears flat (low variance)",
                        artifacts=artifacts,
                        metrics={"file_size": len(data), "unique_samples": len(set(sample))},
                    )

            return ValidationResult(
                stage=self.stage_name,
                status="PASS",
                message="Heightmap validated",
                artifacts=artifacts,
                metrics={"file_size": len(data)},
            )

        except Exception as e:
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message=f"Failed to validate heightmap: {str(e)}",
                artifacts=artifacts,
            )


class PathFinderValidator(Validator):
    """Validator for PathFinder stage."""

    def validate(self, job_id: str) -> ValidationResult:
        artifacts = self._check_artifacts(job_id)

        if not any(artifacts.values()):
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message="PathFinder connectivity report not found",
                artifacts=artifacts,
            )

        # Get PathFinder output
        stage_def = self.registry.get(self.stage_name)
        report_path = stage_def.artifact_path(self.registry.repo_root, job_id, "{job_id}.json")

        try:
            with open(report_path, "r") as f:
                data = json.load(f)

            # Validate structure
            if "routes" not in data:
                return ValidationResult(
                    stage=self.stage_name,
                    status="FAIL",
                    message="Invalid report: missing 'routes' field",
                    artifacts=artifacts,
                )

            routes = data["routes"]
            total_routes = len(routes)
            successful = sum(1 for r in routes if r.get("success", False))
            failed = total_routes - successful

            metrics = {
                "total_routes": total_routes,
                "successful": successful,
                "failed": failed,
                "success_rate": round(successful / total_routes * 100, 1) if total_routes > 0 else 0,
            }

            # Check for isolation
            if failed > successful:
                return ValidationResult(
                    stage=self.stage_name,
                    status="WARN",
                    message=f"High route failure rate: {failed}/{total_routes} failed",
                    artifacts=artifacts,
                    metrics=metrics,
                )

            if total_routes == 0:
                return ValidationResult(
                    stage=self.stage_name,
                    status="WARN",
                    message="No routes found in connectivity report",
                    artifacts=artifacts,
                    metrics=metrics,
                )

            return ValidationResult(
                stage=self.stage_name,
                status="PASS",
                message=f"Validated {successful}/{total_routes} successful routes",
                artifacts=artifacts,
                metrics=metrics,
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message=f"Invalid JSON in connectivity report: {str(e)}",
                artifacts=artifacts,
            )
        except Exception as e:
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message=f"Failed to validate PathFinder output: {str(e)}",
                artifacts=artifacts,
            )


class WorldPreviewValidator(Validator):
    """Validator for WorldPreview stage."""

    def validate(self, job_id: str) -> ValidationResult:
        artifacts = self._check_artifacts(job_id)

        if not any(artifacts.values()):
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message="WorldPreview artifacts not found",
                artifacts=artifacts,
            )

        # Check for complete artifact set
        stage_def = self.registry.get(self.stage_name)
        preview_dir = self.registry.repo_root / "MapGenerator" / "WorldPreview" / "outbox" / job_id

        required_files = ["index.html", "style.css", "main.js", "world.json"]
        required_assets = ["assets/tileset.png", "assets/colormap.png", "assets/legend.png"]

        missing = []
        for file in required_files + required_assets:
            if not (preview_dir / file).exists():
                missing.append(file)

        if missing:
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message=f"Missing files: {', '.join(missing)}",
                artifacts=artifacts,
            )

        # Check file sizes
        index_size = (preview_dir / "index.html").stat().st_size
        world_size = (preview_dir / "world.json").stat().st_size

        metrics = {
            "index_html_bytes": index_size,
            "world_json_bytes": world_size,
            "files_present": len(required_files) + len(required_assets),
        }

        if world_size < 100:
            return ValidationResult(
                stage=self.stage_name,
                status="WARN",
                message="world.json is suspiciously small",
                artifacts=artifacts,
                metrics=metrics,
            )

        return ValidationResult(
            stage=self.stage_name,
            status="PASS",
            message="All preview artifacts validated",
            artifacts=artifacts,
            metrics=metrics,
        )


class ValidatorFactory:
    """Factory for creating stage-specific validators."""

    def __init__(self, registry: StageRegistry):
        self.registry = registry
        self._validators: Dict[str, type] = {
            "heightmap": HeightmapValidator,
            "pathfinder": PathFinderValidator,
            "worldpreview": WorldPreviewValidator,
        }

    def create(self, stage_name: str) -> Validator:
        """Create appropriate validator for stage."""
        stage_lower = stage_name.lower()
        validator_class = self._validators.get(stage_lower, GenericValidator)
        return validator_class(stage_name, self.registry)

    def validate_all(self, job_id: str, stages: Optional[List[str]] = None) -> List[ValidationResult]:
        """Validate multiple stages for a job."""
        if stages is None:
            stages = [s.name for s in self.registry.all_stages()]

        results = []
        for stage_name in stages:
            validator = self.create(stage_name)
            result = validator.validate(job_id)
            results.append(result)

        return results
