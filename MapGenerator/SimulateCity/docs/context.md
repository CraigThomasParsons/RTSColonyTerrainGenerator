# CivicOverreach — Context

CivicOverreach is a MapGenerator pipeline stage responsible for creating
abandoned civic structures and ruins that appear in the world before gameplay begins.

This stage exists to support a colony survival game where players encounter
and reuse failed infrastructure such as:
- abandoned buildings
- collapsed bridges
- overgrown roads

CivicOverreach is NOT responsible for:
- generating playable cities
- balancing gameplay
- ensuring optimal layouts
- producing deterministic results

The goal is believable historical failure, not success.

---

## Relationship to Other Stages

- Terrain (Heightmap) is the root artifact.
- CivicOverreach runs immediately after Heightmap.
- It runs in parallel with:
  - Tiler
  - Weather
  - OldInfrastructure (OpenTTD)

CivicOverreach does not depend on tiles, biomes, or factions.

---

## Engine Philosophy

Game engines (e.g. SimCity, StarCraft) are treated as:
- validators
- visualizers
- sanity checks

They are NOT treated as authoritative generators.

Worldpayload files are the only canonical outputs.
