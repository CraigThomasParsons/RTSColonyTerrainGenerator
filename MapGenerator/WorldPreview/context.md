# WorldPreview — Context

## Role in the Pipeline

WorldPreview is a terminal inspection stage in the MapGenerator pipeline.

It consumes a finalized world payload and produces a static, human-readable
visualization of the world as a file-based artifact.

This stage follows the same inbox/outbox contract as all other modules.

## Why This Stage Exists

Procedural generation fails silently.

WorldPreview forces a human-visible checkpoint where terrain, features, paths,
and biome intent can be visually verified before export into a game engine.

If the preview is wrong, earlier stages are wrong.

## Inputs

- World payload JSON
  - Heightmap data
  - Tile layout
  - Biomes
  - World features
  - Paths and roads

## Outputs

For each job:
```
outbox/<job_id>/
```


Containing a static HTML preview and generated tileset.

The output must be viewable locally without a server.

## Design Principles

- File-backed artifacts over live services
- Zero runtime dependencies
- Deterministic output per job
- Visual clarity over artistic polish

## Non-Goals

- No editing tools
- No simulation
- No engine export
- No runtime interaction beyond inspection

Those concerns belong to later stages.
