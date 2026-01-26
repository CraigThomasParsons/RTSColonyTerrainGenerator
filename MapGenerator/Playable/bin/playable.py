#!/usr/bin/env python3
"""
Playable stage engine.

Pass-through stage that copies the latest worldpayload and emits placeholder
playability labels. This scaffolding is deterministic and safe to replace with
real placement logic.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class JobSelection:
    job_id: str
    input_path: Path
    output_path: Path


def log_line(log_file: Path, job_id: str, level: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{timestamp} [job={job_id}] [stage=playable] {level} {message}"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def iter_candidate_payloads(input_dir: Path) -> Iterable[Path]:
    if not input_dir.exists():
        return []
    return [path for path in input_dir.iterdir() if path.name.endswith(".worldpayload") or path.is_dir()]


def select_job(input_dir: Path, output_dir: Path, job_id: Optional[str]) -> Optional[JobSelection]:
    if job_id:
        candidate = input_dir / f"{job_id}.worldpayload"
        if candidate.exists():
            output_path = output_dir / candidate.name
            return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)
        candidate_dir = input_dir / job_id
        if candidate_dir.exists():
            output_path = output_dir / candidate_dir.name
            return JobSelection(job_id=job_id, input_path=candidate_dir, output_path=output_path)
        return None

    candidates = list(iter_candidate_payloads(input_dir))
    if not candidates:
        return None

    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        job_name = candidate.name
        job_id = job_name.replace(".worldpayload", "")
        output_path = output_dir / job_name
        if output_path.exists():
            continue
        return JobSelection(job_id=job_id, input_path=candidate, output_path=output_path)

    return None


def copy_payload(source: Path, destination: Path) -> None:
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = destination / item.name
            if item.is_dir():
                copy_payload(item, target)
            else:
                target.write_bytes(item.read_bytes())
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())


def write_placeholder_labels(output_dir: Path, job_id: str) -> Path:
    labels_path = output_dir / f"{job_id}.playable.json"
    payload = {
        "version": 1,
        "job_id": job_id,
        "start_zones": [],
        "resource_clusters": [],
        "settlement_labels": [],
        "notes": "placeholder labels - Playable stage scaffolding",
    }
    labels_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return labels_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Playable stage scaffolding")
    parser.add_argument("--input", dest="input_dir", required=True)
    parser.add_argument("--output", dest="output_dir", required=True)
    parser.add_argument("--log-dir", dest="log_dir", required=True)
    parser.add_argument("--job-id", dest="job_id", default=None)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)

    job = select_job(input_dir, output_dir, args.job_id)
    if not job:
        log_line(log_dir / "playable.log", "unknown", "INFO", "No new worldpayloads found")
        return 0

    log_file = log_dir / job.job_id / "playable.log"
    log_line(log_file, job.job_id, "INFO", f"Copying payload from {job.input_path}")

    try:
        copy_payload(job.input_path, job.output_path)
    except Exception as exc:
        log_line(log_file, job.job_id, "ERROR", f"Failed to copy payload: {exc}")
        return 1

    labels_path = write_placeholder_labels(output_dir, job.job_id)
    log_line(log_file, job.job_id, "INFO", f"Wrote labels: {labels_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
