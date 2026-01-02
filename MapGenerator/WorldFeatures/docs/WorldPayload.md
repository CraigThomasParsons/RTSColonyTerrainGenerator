# WorldPayload.md

## World Payload Specification

This document defines the **World Payload** format used by the MapGenerator
pipeline.

A World Payload is the **first fully materialized representation of a map**
and becomes the unit of exchange between downstream generation stages.

---

## 1. Definition

A **World Payload** is a **directory** containing all artifacts required to
describe the state of a generated world at a specific pipeline stage.

> A World Payload is **not** a zip file.  
> It is a directory with a fixed internal structure.

---

## 2. Design Principles

World Payloads are designed to be:

- **Deterministic**  
  Re-running the same inputs must produce the same payload contents.

- **Self-contained**  
  No external files are required to interpret the payload.

- **Human-inspectable**  
  Developers must be able to inspect contents using standard filesystem tools.

- **Immutable once emitted**  
  A stage emits a new payload rather than mutating an existing one.

- **Stage-oriented**  
  Each pipeline stage may add or modify files in the payload,
  but only within its defined responsibility.

---

## 3. Directory Layout (Canonical)
# WorldPayload.md

## World Payload Specification

This document defines the **World Payload** format used by the MapGenerator
pipeline.

A World Payload is the **first fully materialized representation of a map**
and becomes the unit of exchange between downstream generation stages.

---

## 1. Definition

A **World Payload** is a **directory** containing all artifacts required to
describe the state of a generated world at a specific pipeline stage.

> A World Payload is **not** a zip file.  
> It is a directory with a fixed internal structure.

---

## 2. Design Principles

World Payloads are designed to be:

- **Deterministic**  
  Re-running the same inputs must produce the same payload contents.

- **Self-contained**  
  No external files are required to interpret the payload.

- **Human-inspectable**  
  Developers must be able to inspect contents using standard filesystem tools.

- **Immutable once emitted**  
  A stage emits a new payload rather than mutating an existing one.

- **Stage-oriented**  
  Each pipeline stage may add or modify files in the payload,
  but only within its defined responsibility.

---

## 3. Directory Layout (Canonical)

outbox/
└── <id>.worldpayload/
├── <id>.heightmap
├── <id>.maptiles
├── <id>.weather
└── manifest.json


Where `<id>` is the deterministic job identifier shared across all stages.

---

## 4. File Responsibilities

### 4.1 `<id>.heightmap`

- **Format:** Binary (little-endian)
- **Produced by:** Heightmap stage
- **Mutability:** Read-only for all downstream stages

Contains:
- Map dimensions
- Deterministic seed
- Elevation data
- Terrain layers (if present)

Downstream stages **must not**:
- Modify elevations
- Re-normalize data
- Invent new terrain layers

---

### 4.2 `<id>.weather`

- **Format:** JSON
- **Produced by:** Weather Analysis stage
- **Mutability:** Read-only for all downstream stages

Contains:
- Climate analysis
- Rainfall metrics
- Temperature metrics
- Wind exposure
- Frost risk

Used as **signals**, not rules.

---

### 4.3 `<id>.maptiles`

- **Format:** JSON
- **Produced by:** Tiler stage
- **Mutated by:** World-building stages (TreePlanter, WorldFeatures, etc.)

Represents the tile grid of the map.

Example (before TreePlanter):

```json
{
  "x": 12,
  "y": 9,
  "tile_type": "grass",
  "height": 4,
  "terrain_layer": "temperate_inland"
}
```
## Example (after TreePlanter):
```
{
  "x": 12,
  "y": 9,
  "tile_type": "grass",
  "height": 4,
  "terrain_layer": "temperate_inland",
  "decorations": {
    "tree": "canopy"
  }
}
```

Rules:

- Additive changes only

- Existing fields must not be removed

- Semantic data only (no presentation logic)
---
### 4.4 manifest.json

- Format: JSON

- Purpose: Metadata and audit trail

- Consumption: Optional (human / tooling)

Example:

```
{
  "id": "abc123",
  "created_at_utc": "2025-01-03T18:42:11Z",
  "stage": "TreePlanter",
  "inputs": [
    "abc123.heightmap",
    "abc123.maptiles",
    "abc123.weather"
  ],
  "notes": [
    "Deterministic vegetation placement",
    "No man-made features added",
    "Terrain and weather treated as read-only signals"
  ]
}
```
Downstream stages must not depend on this file for correctness.
---

## Outcomes of this stage.

### Passable vs Impassable: which is better?

- Most tiles are passable

- Impassable tiles are exceptions

- You’ll want degrees of passability later so...

### Recommended tile properties

Each tile should expose something like:
```
{
  "passable": true,
  "movement_cost": 1.0,
  "terrain": "grass",
  "height": 42,
  "flags": ["natural"]
}

So we are going to have to add this as another layer or part of the maptiles.
```

# World Payload — Implementation Plan

Location: MapGenerator/WorldFeatures/docs/WorldPayload.md (spec)

Summary
- Provide a small Python library + CLI to create, validate, read, and write World Payload directories matching the spec.

Data model
- `WorldPayload` object:
  - `id: str`, `root: Path`, `created_at_utc: str`, `stage: str`, `inputs: List[str]`, `notes: List[str]`
  - Accessors: `heightmap_path()`, `maptiles_path()`, `weather_path()`, `manifest_path()`

On-disk rules
- Payload is a directory: `<id>.worldpayload/` containing `<id>.heightmap` (binary), `<id>.maptiles` (JSON), `<id>.weather` (JSON), `manifest.json` (JSON).
- Write manifest atomically (temp file + rename).

Validation rules
- Directory name ends with `.worldpayload` and basename matches manifest `id`.
- Required files present.
- Manifest inputs reference the required files.
- Provide an optional immutability check (timestamp/hash) to detect mutation.
- Provide a comparator to enforce additive-only changes for `maptiles` (fail if fields removed or existing values changed).

API & CLI
- Package: `worldpayload` (suggested under `tools/` or `MapGenerator/lib/worldpayload`).
- Core functions:
  - `create_payload(root, id, stage, inputs, notes)`
  - `load_payload(path) -> WorldPayload`
  - `validate_payload(path, strict=True)`
  - `emit_manifest(payload)`
- CLI: `worldpayload-cli validate <path>`, `create`, `inspect`.

Tests
- Unit tests for manifest read/write, atomic write, validation rules, and maptiles comparator.
- Integration test: create temp payload, populate files, run `validate`.
- Use `pytest` and temp directories.

Integration points
- Heightmap stage: write `<id>.heightmap` into payload outbox.
- Tiler: write/modify `<id>.maptiles` (additive only).
- WeatherAnalyses: write `<id>.weather`.
- TreePlanter/WorldFeatures: mutate `maptiles` additively.
- CI: add a job running `worldpayload validate` on pipeline artifacts.

Milestones & estimate
1. Create package skeleton + `WorldPayload` model and `manifest` helpers (1–2 hrs).
2. Implement validators and comparator + unit tests (2–3 hrs).
3. Add CLI and integration test (1–2 hrs).
4. Optional: add binary heightmap reader if needed later.
