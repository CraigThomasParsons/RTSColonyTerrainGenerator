# mapgenctl

`mapgenctl` is a developer control tool for the **MapGenerator pipeline** in
RTSColonyTerrainGenerator.

It provides a filesystem-driven interface for:
- submitting map generation jobs
- observing pipeline progress
- inspecting stage completion
- tailing per-job logs
- running end-to-end test jobs with a live TUI

This tool is intentionally simple and deterministic.
The filesystem is the source of truth.

---

## Philosophy

- **No daemon**
- **No database**
- **No message broker**
- **No websockets**

Pipeline state is inferred exclusively from:
- inbox / outbox artifacts
- job-scoped log files

If a file exists, the stage is done.
If it doesn’t, it isn’t.

This makes the pipeline:
- debuggable
- restartable
- CI-friendly
- SSH-friendly

---

## Directory Layout

```
tools/mapgenctl/
├─ __init__.py
├─ __main__.py        # entrypoint for `python -m tools.mapgenctl`
├─ cli.py             # main CLI + TUI implementation
└─ utils/
   ├─ __init__.py
   ├─ paths.py        # filesystem conventions
   └─ joblog.py       # shared job logger
```

Logs are written to:

```
logs/jobs/<job_id>.log
```

---

## Running mapgenctl

Always run from the **repository root**.

### Basic pipeline run

```bash
python -m tools.mapgenctl run --width 248 --height 248
```

### Run with live TUI (recommended)

```bash
python -m tools.mapgenctl run --width 248 --height 248 --tui
```

### Exit
- `Ctrl+C` or `q` exits cleanly
- Logs remain intact for inspection

---

## Example TUI Output

```
MapGenerator Pipeline
Job ID: 72048b1d-184b-438f-bc1c-7c3313bb1c53
--------------------------------------------------

[✔] heightmap    done
[/] tiler        running
[ ] weather
[ ] treeplanter

Press Ctrl+C (or q) to exit
--------------------------------------------------
Logs (job=72048b1d-184b-438f-bc1c-7c3313bb1c53):
2026-01-06T02:54:48Z [job=...] [stage=mapgenctl] INFO Job submitted width=248 height=248 until=treeplanter
2026-01-06T02:54:48Z [job=...] [stage=heightmap] INFO Stage complete (artifact detected)
```

---

## Job Logging

Each pipeline job has **exactly one log file**:

```
logs/jobs/<job_id>.log
```

All pipeline components (CLI + stages) are expected to append
to the same file using the shared format:

```
<timestamp> [job=<job_id>] [stage=<stage>] <LEVEL> <message>
```

Example:

```
2026-01-06T02:54:48Z [job=abc] [stage=tiler] INFO Placing tiles
```

This allows:
- live TUI tailing
- `grep job=<id>`
- offline debugging
- future JSON or web UI conversion

---

## Stage Completion Semantics

A stage is considered **complete** when its authoritative output
artifact appears in that stage’s outbox.

Examples:
- `heightmap`: `<job_id>.heightmap`
- `tiler`: `<job_id>.maptiles`
- `treeplanter`: `<job_id>.worldpayload`

No other signals are used.

---

## Non-Goals

`mapgenctl` intentionally does NOT:
- orchestrate workers
- schedule jobs
- retry failed stages
- manage concurrency
- provide a GUI

Those concerns belong elsewhere.

---

## Status

This tool is considered **stable** for developer workflows.

It is designed to grow *horizontally* (more stages, better logs),
not *vertically* (more abstraction).

---

###

Control flow of TUI render loop (tools/mapgenctl/mapgenctl.py)
```
start pipeline worker thread
start TUI render loop

while not done:
    read pipeline state
    read new log lines
    render screen
    sleep 100ms

on Ctrl+C:
    signal pipeline to stop
    flush logs
    exit cleanly
```