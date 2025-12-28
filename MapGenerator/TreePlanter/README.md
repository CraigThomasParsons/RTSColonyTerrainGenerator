# TreePlanter

Tree and vegetation placement service for terrain generation.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming tree placement requests
- `outbox/` - Completed vegetation placement data
- `archive/` - Archived processed tree placements

### 1. The inbox will take both output from the tiler and output from the Weather Analyser and plant trees on tiles.
   - This job will not start until they have a <id>.heightmap a <id>.maptiles, a <id>.weather file. (all with the same id)
### 2. The output of Weather Analysis will be the first to package the tiler and the heightmap and the analyses together and put it in the outbox.

# TreePlanter

TreePlanter is a deterministic vegetation placement stage in the
**MapGenerator** pipeline.

Its responsibility is to analyze terrain tiles and weather data, then
add trees and vegetation to the map in a reproducible, non-destructive way.

TreePlanter is the **first stage that emits a complete World Payload**.

---

## Responsibilities

TreePlanter is responsible for:

- Consuming completed outputs from:
  - Heightmap
  - Tiler
  - Weather Analysis
- Deterministically placing vegetation on map tiles
- Mutating **only** the `.maptiles` artifact
- Emitting a complete **World Payload**
- Optionally producing human-readable HTML debug output

TreePlanter is explicitly **not responsible** for:

- Modifying terrain elevation
- Creating man-made features (bridges, ruins, roads)
- Adding caves, mines, or underground access
- Packaging or compressing payloads
- Any form of randomness without deterministic seeding

---

## Pipeline Position
Heightmap
↓
Tiler
↓
Weather Analysis
↓
TreePlanter ← you are here
↓
WorldFeatures
↓
PathFinder


1. Debug Artifacts (Non-Payload)

Debug artifacts are not part of the World Payload.

Examples:

- HTML debug views

- PNG/BMP visualizations

Console samples

Rules:

- Stored in module-local debug/ directories

- Safe to delete at any time

- Never archived

- Never consumed by pipeline stages

Example:

TreePlanter/debug/<id>.html
Tiler/debug/<id>.html