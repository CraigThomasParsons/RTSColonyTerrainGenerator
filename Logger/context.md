# MapGenerator — LogStreamer Context

## Purpose

MapGenerator currently produces many per-stage log files across the pipeline
(Heightmap, Tiler, Weather, TreePlanter, World, etc.).

While these logs are useful locally, debugging and observability across the
entire pipeline is difficult without a single chronological source of truth.

The LogStreamer exists to solve this by aggregating all per-stage logs into
one canonical, append-only log file.

---

## Primary Goal

Produce **one global log file**:

logs/mapgen.log

This file represents the authoritative, ordered history of everything that
happened during MapGenerator execution.

---

## Non-Goals

The LogStreamer MUST NOT:
- Rotate logs
- Delete logs
- Modify or truncate source log files
- Perform job orchestration
- Infer progress or success
- Make decisions based on log contents
- Replace per-stage logs

It is intentionally dumb.

---

## Inputs

The LogStreamer reads log files from stage-specific directories:

Heightmap/logs/*.log  
Tiler/logs/*.log  
Weather/logs/*.log  
TreePlanter/logs/*.log  
World/logs/*.log  

Additionally, job-scoped logs may exist under:

logs/jobs/<job-id>/*.log

These layouts are authoritative and should not be changed by the LogStreamer.

---

## Output

The LogStreamer appends normalized TEXT log entries to:

logs/mapgen.log

This file is:
- Append-only
- Never truncated
- Written by the LogStreamer only

No other component may write directly to mapgen.log.

Canonical line format (mapgenctl-style):

2026-01-07T16:50:42Z [job=0ab66106-97fe-4fe4-8133-3ff67fde706e] [stage=tiler] INFO Stage complete (artifact detected)

Requirements:
- Timestamp must be UTC in ISO-8601 (`YYYY-MM-DDThh:mm:ssZ`).
- Job ID extracted from directory structure (logs/jobs/<job-id>/...) or defaults to `unknown`.
- Stage inferred from log file path components.
- Original message appears after the level token.
---

## Log Normalization Rules

Each output line in mapgen.log MUST contain:

- timestamp (UTC, ISO-8601)
- stage (derived from log file path)
- job_id (derived from directory name if present, otherwise "unknown")
- log level (if detectable, otherwise "INFO")
- original message

Example output format:

2026-01-22T05:37:55Z [job=0ab66106-97fe-4fe4-8133-3ff67fde706e] [stage=tiler] INFO Processing tile 12,8

If metadata cannot be inferred, use safe defaults rather than failing.

---

## Stage Identification

Stage name is inferred from the log file path:

Heightmap/logs/...   → stage=heightmap  
Tiler/logs/...       → stage=tiler  
Weather/logs/...     → stage=weather
TreePlanter/logs/... → stage=treeplanter
World/logs/...       → stage=world
logs/jobs/<job-id>/... → stage=job-specific