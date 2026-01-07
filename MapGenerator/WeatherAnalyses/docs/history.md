# Heightmap Generator – Project Context

### Weather Analyses

## Purpose

The Heightmap Generator is a standalone component of the MapGenerator pipeline.
Its responsibility is to generate deterministic terrain heightmaps from queued
job descriptions, using a fault-line algorithm.

This component does **not** perform tiling, rendering, or gameplay logic.
It produces exactly one output file per job, which is then consumed by the Tiler.

---

## High-Level Architecture

Pipeline model (filesystem-backed queue):

API
→ writes JSON job file
→ Heightmap/inbox/

systemd (.path unit)
→ triggers Bash worker

Bash worker
→ invokes Rust heightmap engine
→ writes output file

Heightmap/outbox/
→ symlink to Tiler/inbox/

---

## Technology Choices (Locked In)

- Orchestration: systemd (user units)
- Queue mechanism: filesystem (inbox / outbox folders)
- Worker glue: Bash
- Heightmap engine: Rust (compiled binary)
- API role: enqueue jobs only (writes JSON files)
- Output: single binary heightmap file per job
- Determinism: required (seeded RNG)

Docker is used for the API only.
The worker and engine are intended to run natively on the host.

---

## Heightmap Engine Responsibilities

The Rust heightmap engine:

- Accepts a job JSON file via CLI arguments
- Parses a strongly-typed job schema
- Runs a fault-line terrain generation algorithm
- Accumulates signed height values
- Normalizes values to 0–255
- Writes exactly one binary output file
- Logs progress to stdout
- Exits non-zero on failure

The engine is intentionally verbose:
- Descriptive variable and function names
- Heavy comments (roughly every 2–3 lines)
- No single-character variable names

---

## Heightmap Job JSON Schema (Current)

The engine expects job files with this structure:

```json
{
  "job_id": "string",
  "map_width_in_cells": 256,
  "map_height_in_cells": 256,
  "fault_line_iteration_count": 200,
  "random_seed": 123456789,
  "requested_at_utc": "ISO-8601 timestamp"
}
```

Notes:

- fault_line_iteration_count is optional

- If omitted, the engine applies a conservative default

- The schema is considered v1 and stable

Heightmap Engine CLI Contract
```
heightmap-engine \
  --job-file <path-to-job.json> \
  --output-file <path-to-output.heightmap>
```

Exactly one output file is produced per invocation.

Current Status

- Heightmap engine exists and implements fault-line generation

- Docker Compose issues resolved

- API container mounts Heightmap directory correctly

- Project has already done:

  - Bash worker

  - systemd queue wiring

### What is next?
 I want heightmaps to build data and store based on more complex algorithms.
   Then in later steps take this data in mind when placing trees, rivers, outcropping.
   Basically, I think there is a lot more to do in the direction of the heightmapper.

- slope calculation
- river flow direction
- basin detection
- edge-aware smoothing
- erosion simulation
- river carving that respects slopes

In World features there will be hopefully, lakes, rivers, caves, stone outcroppings.

### Another idea, where there is ridges at the lines
```
    - 0 to 79 Water,
    - 80 to 159 Land,
    - 160 to 219 PineMountain
    - 210 to end RockMountain
```

We want to do edge-aware smoothing
-> We also want to come up with possible ramps to pass to the PineMountain and RockMountains
-> We also want to come up with possible beaches.

### Context.md was generated to capture the implementation plans.