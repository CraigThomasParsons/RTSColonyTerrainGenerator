"""Pipeline controller for managing job execution."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PipelineConfig:
    """Configuration for a pipeline run."""

    width: int = 64
    height: int = 64
    until_stage: str = "WorldPreview"
    repo_root: Optional[Path] = None


class PipelineController:
    """Manages pipeline job orchestration via mapgenctl."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.job_id: Optional[str] = None

    def start(self) -> bool:
        """Launch a pipeline run using mapgenctl.

        Returns True if process started successfully.
        """
        command = [
            sys.executable,
            "-m",
            "tools.mapgenctl",
            "submit-heightmap",
            "--width",
            str(self.config.width),
            "--height",
            str(self.config.height),
        ]

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.config.repo_root) if self.config.repo_root else None,
            )
            return True
        except Exception as e:
            print(f"Failed to start pipeline: {e}")
            return False

    def stop(self) -> None:
        """Terminate the pipeline process if running."""
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

    def is_running(self) -> bool:
        """Check if the pipeline process is still active."""
        if self.process is None:
            return False
        return self.process.poll() is None

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for pipeline completion and return exit code."""
        if self.process is None:
            return -1
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return -1
