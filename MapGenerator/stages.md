
```
# MapGenerator Stages

This document is the quick-reference guide for the MapGenerator pipeline. It lists
every stage, its purpose, and the precise inbox/outbox artifacts it reads and writes.

The pipeline is file-driven. Each stage is a stateless transformer: one input → one output.

---

## Pipeline Overview (Current)

```
[Job Spec]
  │
  ▼
Heightmap
  ├─ inbox:  <id>.json
  └─ outbox: <id>.heightmap
  │
  ├──────────────► WeatherAnalyses
  │                 ├─ inbox:  <id>.heightmap
  │                 └─ outbox: <id>.weather
  ▼
Tiler
  ├─ inbox:  <id>.heightmap
  └─ outbox: <id>.maptiles
  │
  ▼
TreePlanter
  ├─ inbox:  <id>.heightmap + <id>.maptiles + <id>.weather
  └─ outbox: <id>.worldpayload/
         ├─ <id>.heightmap
         ├─ <id>.maptiles
         ├─ <id>.weather
         └─ manifest.json (+ vegetation)
  │
  ▼
WorldFeatures
  ├─ inbox:  <id>.worldpayload/
  └─ outbox: <id>.worldpayload/ (augmented)
  │
  ├──────────────► AncientCivilization
  │                 └─ outbox: settlement/ruins/path artifacts (see below)
  ▼
PathFinder
  ├─ inbox:  <id>.worldpayload/
  └─ outbox: <id>.json (connectivity report + routes)
  │
  ├──────────────► InfrastructureBuilder (planned)
  │                 └─ outbox: <id>.worldpayload/ (mutated)
  ▼
Playable
  ├─ inbox:  <id>.worldpayload/
  └─ outbox: <id>.worldpayload + <id>.playable.json
  │
  ├──────────────► StargusExport
  │                 └─ outbox: <id>.chk + <id>.scm
  │
  ├──────────────► CartridgeManufacturer
  │                 └─ outbox: <id>.wcar + <id>.chk + <id>.scm
  ▼
WorldPreview
  ├─ inbox:  <id>.json (PathFinder output)
  └─ outbox: <id>/index.html (+ assets)
  │
  ▼
WorldSnapshot
  ├─ inbox:  WorldPreview outbox/<id>/index.html
  └─ outbox: <id>.png
```

---

## Stage-by-Stage Details

### Heightmap
**Purpose:** Generate the terrain height grid from a job spec.

**Inbox:**
- MapGenerator/Heightmap/inbox/<id>.json

**Outbox:**
- MapGenerator/Heightmap/outbox/<id>.heightmap

**Downstream fan-out:** Copies the heightmap into Tiler and WeatherAnalyses inboxes.

---

### WeatherAnalyses
**Purpose:** Derive analytical layers (slope, flow, basins) from the heightmap.

**Inbox:**
- MapGenerator/WeatherAnalyses/inbox/<id>.heightmap

**Outbox:**
- MapGenerator/WeatherAnalyses/outbox/<id>.weather

---

### Tiler
**Purpose:** Convert heightmap cells into renderable tiles.

**Inbox:**
- MapGenerator/Tiler/inbox/<id>.heightmap

**Outbox:**
- MapGenerator/Tiler/outbox/<id>.maptiles

---

### TreePlanter
**Purpose:** Add deterministic vegetation and emit the first World Payload.

**Inbox (required):**
- <id>.heightmap
- <id>.maptiles
- <id>.weather

**Outbox:**
- MapGenerator/TreePlanter/outbox/<id>.worldpayload/
  - <id>.heightmap
  - <id>.maptiles
  - <id>.weather
  - manifest.json (+ vegetation metadata)

---

### WorldFeatures
**Purpose:** Add key gameplay features (ramps, caves/mines, resource hints, rivers).

**Inbox:**
- MapGenerator/WorldFeatures/inbox/<id>.worldpayload/ (from TreePlanter outbox)

**Outbox:**
- MapGenerator/WorldFeatures/outbox/<id>.worldpayload/ (augmented)

---

### PathFinder
**Purpose:** Analyze traversability and connectivity. Emit routes and requests.

**Inbox:**
- MapGenerator/PathFinder/inbox/<id>.worldpayload/ (from WorldFeatures outbox)

**Outbox (current):**
- MapGenerator/PathFinder/outbox/<id>.json
  - Connectivity graph
  - Routes
  - Infrastructure requests (bridges/roads/tunnels)

---

### InfrastructureBuilder (Planned)
**Purpose:** Apply PathFinder requests to the world: roads, bridges, tunnels.

**Inbox:**
- MapGenerator/InfrastructureBuilder/inbox/<id>.json (PathFinder report)

**Side input (lookup):**
- MapGenerator/WorldFeatures/outbox/<id>.worldpayload/

**Outbox:**
- MapGenerator/InfrastructureBuilder/outbox/<id>.worldpayload/ (mutated)

---

### AncientCivilization
**Purpose:** Synthesize ruins, proto-settlements, and ancient paths (deterministic).

**Inbox:**
- MapGenerator/AncientCivilization/inbox/<id>.worldpayload/ (from WorldFeatures)

**Outbox (per job):**
- settlements.json
- ruins.json
- ancient_paths.json
- reclaimed_resources.json
- collapse_reason.txt

---

### WorldPreview
**Purpose:** Human-facing inspection of the current world state.

**Inbox:**
- MapGenerator/WorldPreview/inbox/<id>.json (from PathFinder outbox)

**Outbox:**
- MapGenerator/WorldPreview/outbox/<id>/index.html
- style.css, main.js, world.json, assets/

---

### WorldSnapshot
**Purpose:** Render a PNG snapshot of WorldPreview output (headless Playwright).

**Inbox:**
- MapGenerator/WorldPreview/outbox/<id>/index.html

**Outbox:**
- MapGenerator/WorldSnapshot/outbox/<id>.png

---

### Playable
**Purpose:** Make payloads immediately playable by labeling starts/resources.

**Inbox:**
- MapGenerator/Playable/inbox/<id>.worldpayload (from WorldFeatures or InfrastructureBuilder)

**Outbox:**
- MapGenerator/Playable/outbox/<id>.worldpayload
- MapGenerator/Playable/outbox/<id>.playable.json

---

### StargusExport
**Purpose:** Export a World Payload to StarCraft-compatible CHK/SCM.

**Inbox (current):**
- MapGenerator/StargusExport/inbox/<id>.worldpayload (or Playable outbox via wrapper)

**Outbox:**
- MapGenerator/StargusExport/outbox/<id>.chk
- MapGenerator/StargusExport/outbox/<id>.scm

---

### CartridgeManufacturer
**Purpose:** Produce WCAR cartridges and validate via Stratagus harness.

**Inbox (current):**
- MapGenerator/CartridgeManufacturer/inbox/<id>.worldpayload (or Playable outbox via wrapper)

**Outbox:**
- MapGenerator/CartridgeManufacturer/outbox/<id>.wcar
- MapGenerator/CartridgeManufacturer/outbox/<id>.chk
- MapGenerator/CartridgeManufacturer/outbox/<id>.scm

---

## Test/Validation Hooks

- MapGenerator/tools/pipeline_ai_test can validate WorldPreview and WorldSnapshot.
- WorldSnapshot is the canonical “rendered truth” for quick human review.