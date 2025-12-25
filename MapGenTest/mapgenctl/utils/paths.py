"""
Filesystem path definitions for the MapGenerator pipeline.

This module defines canonical locations used by mapgenctl
to interact with the pipeline.

All path logic lives here to avoid duplication and drift.
"""

from pathlib import Path

def repo_root() -> Path:
    """
    Resolve the repository root based on this file location.
    """
    return Path(__file__).resolve().parents[3]


def stage_dir(stage: str) -> Path:
    """
    Return the MapGenerator directory for a pipeline stage.
    """
    return repo_root() / "MapGenerator" / stage.capitalize()


def stage_inbox(stage: str) -> Path:
    return stage_dir(stage) / "inbox"


def stage_outbox(stage: str) -> Path:
    return stage_dir(stage) / "outbox"


def stage_archive(stage: str) -> Path:
    return stage_dir(stage) / "archive"


def project_root() -> Path:
    """
    Return the repository root directory.

    Assumes mapgenctl lives at:
    <repo>/MapGenTest/mapgenctl/
    """
    return Path(__file__).resolve().parents[3]


def map_generator_root() -> Path:
    """
    Return the MapGenerator pipeline root.
    """
    return project_root() / "MapGenerator"


def heightmap_stage_root() -> Path:
    """
    Return the Heightmap stage root directory.
    """
    return map_generator_root() / "Heightmap"


def heightmap_inbox() -> Path:
    """
    Directory where heightmap job JSON files are submitted.
    """
    return heightmap_stage_root() / "inbox"


def heightmap_outbox() -> Path:
    """
    Directory where heightmap output files are written.
    """
    return heightmap_stage_root() / "outbox"
