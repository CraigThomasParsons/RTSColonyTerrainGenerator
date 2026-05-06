# InfrastructureBuilder Implementation Plan

## Goal

Implement the `InfrastructureBuilder` stage. This module resolves connectivity issues identified by the `PathFinder` stage by modifying the world to add roads, bridges, and tunnels.

## Inputs

1. **ConnectivityReport** (`.json`) from `PathFinder/outbox`.
    * Contains `job_id` and `requests`.
2. **WorldPayload** (`.worldpayload`) from `WorldFeatures/outbox` (via lookup).
    * Contains the actual map tiles to modify.

## Outputs

1. **WorldPayload** (`.worldpayload`) to `InfrastructureBuilder/outbox`.
    * The modified world with new infrastructure decorations/terrain.

## Methodology: TYS (Implement -> Verify -> Loop)

### Phase 1: Setup & Inputs

1. **Project Shell**: Gradle setup (Kotlin), Systemd units.
2. **Input Parsing**:
    * Read `ConnectivityReport`.
    * Locate and read the corresponding `WorldPayload` (using `job_id`).
    * Verify we have both "What to fix" and "The World to fix".

### Phase 2: Infrastructure Logic

1. **Resolver Engine**:
    * Process `requests` from the report.
    * **Bridge**: If request is over Water -> Change terrain/decoration to Bridge.
    * **Road**: If request is over Land (high cost) -> Add Road decoration.
    * **Tunnel**: (Optional) If request is blocked by Mountain.
2. **Mutation**:
    * Apply changes to `TileInfo` objects.
    * Deterministic updates.

### Phase 3: Output & Integration

1. **Output Writer**: Write the mutated `WorldPayload` to `outbox`.
2. **Systemd**: Wire up to watch `PathFinder/outbox`.

## Verification (AI Tool)

* **Command**: `gradle run --args="--report ../PathFinder/outbox/JOB.json"`
* **Check**:
  * Output files exist.
  * Tiles at request coordinates have changed (e.g. `decorations` now has `road`).

## Next Steps

Initialize the project.
