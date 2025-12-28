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
