# Pathfinder Implementation Plan

## Goal

Implement the `PathFinder` stage in Kotlin to simulate trade connectivity between settlements (world features). This stage identifies reachable paths, isolated nodes, and necessary infrastructure (roads, bridges).

## Methodology: TYS (Implement -> Verify -> Loop)

We will build this stage incrementally, verifying each step with `pipeline_ai_test.py` before proceeding.

## Phase 1: Project Setup & Input Parsing

**Goal:** Successfully compile and read the `WorldFeatures` payload.

1. **Setup Gradle**: Create `build.gradle.kts` and `settings.gradle.kts` in `MapGenerator/PathFinder`.
    * Dependencies: `kotlinx-serialization-json`, `slf4j-simple`.
2. **Define Models**: Replicate `ParsedPayload`, `TileInfo`, `WorldFeature` data classes to match `WorldFeatures` output.
3. **Implement `PathFinderApp`**:
    * Main entry point.
    * Argument parsing (input/output paths).
    * JSON parsing logic.
4. **TYS Check**:
    * Run `PathFinder` against a sample `WorldFeatures` output.
    * Verify it prints "Parsed X tiles and Y features".

## Phase 2: Graph & Pathfinding Core

**Goal:** Build a connectivity graph between all "settlements" (Features).

1. **Define Nodes**: Treat `WorldFeature` items (e.g., `lumber`, `cavern`, `ramp`) as graph nodes.
2. **Implement A* / Dijkstra**:
    * **Cost Function**:
        * Base Terrain: Grass=1, Dirt=1.
        * Decorations: Tree=2 (needs clearing), Rock=3.
        * Height Delta: Increase cost with slope.
        * Water/Lava: Impassable (infinite cost) unless bridging logic is added (later).
3. **Simulation Loop**:
    * For each pair of features (A, B):
        * Calculate path.
        * Store result (Success/Fail, Cost, Path).
4. **TYS Check**:
    * Run against a map with known barriers (e.g., water).
    * Verify reachable pairs are connected.
    * Verify unreachable pairs are flagged.

## Phase 3: Infrastructure Analysis & Output

**Goal:** Generate the "Request" list for the next stage.

1. **Analyze Failures**:
    * If path failed due to Water -> Request Bridge.
    * If path is high cost due to Forest -> Request Clearing.
    * (Simple heuristics for v1).
2. **Generate Output Payload**:
    * Definition of `ConnectivityReport` JSON.
    * Include: `graph` (edges), `requests` (infrastructure).
    * Write to outbox.
3. **TYS Check**:
    * Verify JSON output is valid and contains expected data.

## Phase 4: System Integration

**Goal:** Run as a daemon service.

1. **Wrapper Script**: Create `bin/run-pathfinder.sh` (or `produce_consume_loop` equivalent).
2. **Systemd Service**: Create `systemd/pathfinder.service`.
3. **TYS Check**:
    * Start service.
    * Drop file in `WorldFeatures` outbox.
    * Watch `PathFinder` process and produce output.

## Technical details

- **Language**: Kotlin (JVM).
* **Build System**: Gradle (Kotlin DSL).
* **Libraries**: `kotlinx.serialization`.
* **Logging**: Structured JSON logging (for AI tools).

## Next Steps

Trigger Phase 1 implementation.
