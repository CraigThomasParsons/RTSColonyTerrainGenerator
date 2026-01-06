# tools/joblog.py
from __future__ import annotations

import datetime
from pathlib import Path


def project_root() -> Path:
    """
    Resolve RTSColonyTerrainGenerator root directory.

    Assumes this file lives in RTSColonyTerrainGenerator/tools/.
    """
    return Path(__file__).resolve().parents[1]


def jobs_log_dir() -> Path:
    """
    Central job log directory.
    """
    return project_root() / "logs" / "jobs"


def job_log_path(job_id: str) -> Path:
    """
    Resolve the log file path for a job.
    """
    return jobs_log_dir() / f"{job_id}.log"


class JobLogger:
    """
    Minimal append-only job logger.

    All pipeline components must emit lines in the same format.
    """

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.path = job_log_path(job_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _ts(self) -> str:
        return (
            datetime.datetime.now(datetime.UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    def log(self, stage: str, level: str, message: str) -> None:
        line = (
            f"{self._ts()} "
            f"[job={self.job_id}] "
            f"[stage={stage}] "
            f"{level.upper()} {message}\n"
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)

    def info(self, stage: str, message: str) -> None:
        self.log(stage, "INFO", message)

    def warn(self, stage: str, message: str) -> None:
        self.log(stage, "WARN", message)

    def error(self, stage: str, message: str) -> None:
        self.log(stage, "ERROR", message)
