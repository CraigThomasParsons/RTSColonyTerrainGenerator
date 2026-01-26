"""Stage registry for dynamic configuration of pipeline stages.

Provides unified access to stage metadata including artifact paths,
timeouts, dependencies, and validation rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class StageDefinition:
    """Metadata for a single pipeline stage."""

    name: str
    timeout_seconds: int = 120
    artifact_patterns: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    description: str = ""

    def artifact_path(self, repo_root: Path, job_id: str, pattern: str) -> Path:
        """Resolve artifact path for this stage."""
        return repo_root / "MapGenerator" / self.name / "outbox" / pattern.format(job_id=job_id)


class StageRegistry:
    """Central registry for all pipeline stages."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._stages: Dict[str, StageDefinition] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default stage configurations."""
        self.register(
            StageDefinition(
                name="Heightmap",
                timeout_seconds=120,
                artifact_patterns=["{job_id}.heightmap"],
                description="Generates base terrain heightmap",
            )
        )
        self.register(
            StageDefinition(
                name="Tiler",
                timeout_seconds=120,
                artifact_patterns=["{job_id}.maptiles"],
                dependencies=["Heightmap"],
                description="Converts heightmap to tile grid",
            )
        )
        self.register(
            StageDefinition(
                name="WeatherAnalyses",
                timeout_seconds=120,
                artifact_patterns=["{job_id}.weather"],
                dependencies=["Heightmap"],
                description="Analyzes climate and weather patterns",
            )
        )
        self.register(
            StageDefinition(
                name="TreePlanter",
                timeout_seconds=180,
                artifact_patterns=["{job_id}.worldpayload"],
                dependencies=["Tiler", "WeatherAnalyses"],
                description="Places vegetation based on climate",
            )
        )
        self.register(
            StageDefinition(
                name="WorldFeatures",
                timeout_seconds=180,
                artifact_patterns=["{job_id}.worldpayload"],
                dependencies=["TreePlanter"],
                description="Adds ramps, caverns, and lumber features",
            )
        )
        self.register(
            StageDefinition(
                name="PathFinder",
                timeout_seconds=180,
                artifact_patterns=["{job_id}.json"],
                dependencies=["WorldFeatures"],
                description="Analyzes connectivity and generates routes",
            )
        )
        self.register(
            StageDefinition(
                name="AncientCivilization",
                timeout_seconds=120,
                artifact_patterns=[
                    "{job_id}.settlements.json",
                    "{job_id}.ruins.json",
                    "{job_id}.ancient_paths.json",
                    "{job_id}.reclaimed_resources.json",
                    "{job_id}.collapse_reason.txt",
                ],
                dependencies=["WorldFeatures"],
                description="Generates historical civilization artifacts",
            )
        )
        self.register(
            StageDefinition(
                name="WorldPreview",
                timeout_seconds=60,
                artifact_patterns=["{job_id}/index.html"],
                dependencies=["PathFinder"],
                description="Renders interactive world preview",
            )
        )

    def register(self, stage: StageDefinition) -> None:
        """Register a stage definition."""
        self._stages[stage.name.lower()] = stage

    def get(self, stage_name: str) -> Optional[StageDefinition]:
        """Get stage definition by name (case-insensitive)."""
        return self._stages.get(stage_name.lower())

    def all_stages(self) -> List[StageDefinition]:
        """Get all registered stages."""
        return list(self._stages.values())

    def check_artifacts(self, stage_name: str, job_id: str) -> Dict[str, bool]:
        """Check which artifacts exist for a given stage and job."""
        stage = self.get(stage_name)
        if not stage:
            return {}

        results = {}
        for pattern in stage.artifact_patterns:
            path = stage.artifact_path(self.repo_root, job_id, pattern)
            results[pattern] = path.exists()
        return results

    def get_dependency_chain(self, stage_name: str) -> List[str]:
        """Get ordered list of dependencies for a stage."""
        stage = self.get(stage_name)
        if not stage:
            return []

        chain = []
        for dep in stage.dependencies:
            chain.extend(self.get_dependency_chain(dep))
            if dep not in chain:
                chain.append(dep)
        return chain
