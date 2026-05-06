# Playable — Context

## Purpose

Playable prepares the world for RTS gameplay by enforcing start-zone fairness and
resource accessibility. It is the last gameplay-shaping stage before export.

It does not create new terrain; it labels and augments the world payload with
information exporters can use to place starts and resources deterministically.

## Pipeline Position

WorldFeatures → Playable → StargusExport / CartridgeManufacturer

If InfrastructureBuilder exists, Playable should consume its output instead of
WorldFeatures directly.

## Responsibilities

Playable must:
- Choose start zones on traversable terrain
- Ensure each start has nearby wood + ore/stone clusters
- Label expansions with distance and path cost tiers
- Emit labels deterministically

## Non-Responsibilities

Playable must not:
- Mutate core terrain geometry
- Randomly place resources
- Add features that belong to WorldFeatures or InfrastructureBuilder

## Determinism

Same input → same output. Tie-breaks use stable ordering on job_id and tile
coordinates.
