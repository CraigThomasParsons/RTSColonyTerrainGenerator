"""
Job discovery and indexing for the TUI.

This module provides utilities to discover and list jobs that have
log files in the logs/jobs/ directory. It's used to populate job
selection interfaces and provide an overview of pipeline activity.

Purpose:
    When a developer wants to view logs for a previous job, they need
    a way to see what jobs exist. This module scans the log directory
    and returns structured information about each discovered job.
"""

from pathlib import Path
from typing import List, Dict

# Root directory for job logs
# Relative path assumes execution from the tools/ directory
LOG_ROOT = Path("logs/jobs")


def discover_jobs() -> List[Dict]:
    """
    Scan the log directory and return information about discovered jobs.

    This function looks for job directories containing stage log files
    and builds a summary of each job including which stages have logs
    and when they were last modified.

    Returns:
        List[Dict]: A list of job dictionaries, sorted by most recently
                   modified first. Each dictionary contains:
                   - job_id (str): The job's unique identifier
                   - stages (List[str]): Stage names that have log files
                   - last_mtime (float): Most recent modification time

    Example:
        >>> jobs = discover_jobs()
        >>> jobs[0]
        {'job_id': 'abc-123', 'stages': ['heightmap', 'tiler'], 'last_mtime': 1705320000.0}

    Note:
        - Jobs are sorted by modification time (newest first)
        - Directories without .log.jsonl files are skipped
        - Returns empty list if LOG_ROOT doesn't exist
    """
    jobs = []

    # Guard against missing log directory
    if not LOG_ROOT.exists():
        return jobs

    # Iterate through each subdirectory in the log root
    for job_dir in LOG_ROOT.iterdir():
        # Skip files - we only care about job directories
        if not job_dir.is_dir():
            continue

        # Find all stage log files for this job
        # Log files follow the pattern: <stage>.log.jsonl
        stage_logs = sorted(job_dir.glob("*.log.jsonl"))

        # Skip jobs with no log files
        if not stage_logs:
            continue

        # Get the most recent modification time across all stage logs
        # This helps sort jobs by activity for the UI
        last_mtime = max(f.stat().st_mtime for f in stage_logs)

        # Extract stage names from log filenames
        # Removes the ".log" suffix that glob includes in stem
        stages = [f.stem.replace(".log", "") for f in stage_logs]

        # Build the job summary dictionary
        jobs.append({
            "job_id": job_dir.name,
            "stages": stages,
            "last_mtime": last_mtime,
        })

    # Sort by modification time, most recent first
    # This puts the active/recent jobs at the top of lists
    jobs.sort(key=lambda j: j["last_mtime"], reverse=True)

    return jobs
