"""
Filesystem path definitions for the MapGenerator pipeline.

This module defines canonical locations used by mapgenctl to interact with
the pipeline. All path logic is centralized here to avoid duplication and
ensure consistency across the codebase.

Purpose:
    The MapGenerator pipeline is filesystem-driven—each stage reads from an
    inbox directory and writes to an outbox directory. This module provides
    a single source of truth for resolving these paths, making the code more
    maintainable and less prone to path-related bugs.

Design Decisions:
    - All functions return pathlib.Path objects for cross-platform compatibility
    - Paths are resolved relative to the repository root, not the current directory
    - Stage names are normalized (capitalized) to match the directory structure
"""

from pathlib import Path


def repo_root() -> Path:
    """
    Resolve the repository root directory.

    The repository root is determined by traversing up from this file's location.
    This file lives at: <repo>/tools/mapgenctl/utils/paths.py
    So we go up 3 parent directories to reach the repo root.

    Returns:
        Path: Absolute path to the RTSColonyTerrainGenerator repository root.

    Example:
        >>> repo_root()
        PosixPath('/home/user/Code/RTSColonyTerrainGenerator')
    """
    return Path(__file__).resolve().parents[3]


# Maps logical stage names to their actual directory names.
# Most stages use capitalized names, but some have special names.
STAGE_DIRECTORY_MAP = {
    "heightmap": "Heightmap",
    "tiler": "Tiler",
    "weather": "WeatherAnalyses",
    "treeplanter": "TreePlanter",
}


def stage_dir(stage: str) -> Path:
    """
    Return the MapGenerator directory for a pipeline stage.

    Each pipeline stage (heightmap, tiler, etc.) has its own directory
    under MapGenerator/ containing inbox/, outbox/, and archive/ subdirs.

    Args:
        stage: Logical name of the pipeline stage (e.g., "heightmap", "tiler").
               Uses STAGE_DIRECTORY_MAP for lookup, falls back to capitalized name.

    Returns:
        Path: Absolute path to the stage's root directory.

    Example:
        >>> stage_dir("heightmap")
        PosixPath('/home/user/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap')
        >>> stage_dir("weather")
        PosixPath('/home/user/Code/RTSColonyTerrainGenerator/MapGenerator/WeatherAnalyses')
    """
    dir_name = STAGE_DIRECTORY_MAP.get(stage, stage.capitalize())
    return repo_root() / "MapGenerator" / dir_name


def stage_inbox(stage: str) -> Path:
    """
    Return the inbox directory for a pipeline stage.

    The inbox is where job request files are placed for the stage to process.
    Each stage monitors its inbox for new work.

    Args:
        stage: Logical name of the pipeline stage.

    Returns:
        Path: Absolute path to the stage's inbox directory.
    """
    return stage_dir(stage) / "inbox"


def stage_outbox(stage: str) -> Path:
    """
    Return the outbox directory for a pipeline stage.

    The outbox is where completed artifacts are written. The presence of
    an artifact in the outbox signals that the stage has completed.

    Args:
        stage: Logical name of the pipeline stage.

    Returns:
        Path: Absolute path to the stage's outbox directory.
    """
    return stage_dir(stage) / "outbox"


def stage_archive(stage: str) -> Path:
    """
    Return the archive directory for a pipeline stage.

    The archive stores processed job files after completion. This allows
    the inbox to stay clean while preserving job history for debugging.

    Args:
        stage: Logical name of the pipeline stage.

    Returns:
        Path: Absolute path to the stage's archive directory.
    """
    return stage_dir(stage) / "archive"


def project_root() -> Path:
    """
    Return the repository root directory.

    Note:
        This is an alias for repo_root(). Both functions exist for backward
        compatibility and semantic clarity in different contexts.

    Returns:
        Path: Absolute path to the repository root.
    """
    return Path(__file__).resolve().parents[3]


def map_generator_root() -> Path:
    """
    Return the MapGenerator pipeline root directory.

    The MapGenerator directory contains all pipeline stage directories
    (Heightmap/, Tiler/, WeatherAnalyses/, TreePlanter/).

    Returns:
        Path: Absolute path to the MapGenerator directory.
    """
    return project_root() / "MapGenerator"


def heightmap_stage_root() -> Path:
    """
    Return the Heightmap stage root directory.

    This is a convenience function for the most commonly accessed stage.
    The Heightmap stage is the entry point to the pipeline.

    Returns:
        Path: Absolute path to the Heightmap stage directory.
    """
    return map_generator_root() / "Heightmap"


def heightmap_inbox() -> Path:
    """
    Return the directory where heightmap job JSON files are submitted.

    New jobs enter the pipeline by placing a JSON job specification
    in this directory. The Heightmap stage polls this directory for work.

    Returns:
        Path: Absolute path to the Heightmap inbox directory.
    """
    return heightmap_stage_root() / "inbox"


def heightmap_outbox() -> Path:
    """
    Return the directory where heightmap output files are written.

    When the Heightmap stage completes, it writes a .heightmap binary
    file to this directory. Downstream stages watch this directory
    to know when to begin their work.

    Returns:
        Path: Absolute path to the Heightmap outbox directory.
    """
    return heightmap_stage_root() / "outbox"
