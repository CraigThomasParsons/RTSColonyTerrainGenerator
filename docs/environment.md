# MapGenerator Environment Configuration

This document describes how environment variables are used across the
MapGenerator pipeline.

The core rule is simple:

> **Automated pipeline directories are sacred.  
> Debug output is strictly human-only.**

---

## Directory Philosophy

### Machine-Owned (DO NOT TOUCH MANUALLY)

These directories are consumed exclusively by automated processes:

- `inbox/`
- `outbox/`
- `archive/`
- `failed/`

They form a strict pipeline contract between stages.

Human-written files or debug artifacts must NEVER appear here.

---

### Human-Owned (Safe to Inspect, Delete, Modify)

Debug output is written to a dedicated directory:

# MapGenerator Environment Configuration

This document describes how environment variables are used across the
MapGenerator pipeline.

The core rule is simple:

> **Automated pipeline directories are sacred.  
> Debug output is strictly human-only.**

---

## Directory Philosophy

### Machine-Owned (DO NOT TOUCH MANUALLY)

These directories are consumed exclusively by automated processes:

- `inbox/`
- `outbox/`
- `archive/`
- `failed/`

They form a strict pipeline contract between stages.

Human-written files or debug artifacts must NEVER appear here.

---

### Human-Owned (Safe to Inspect, Delete, Modify)

Debug output is written to a dedicated directory:

MAPGEN_DEBUG_OUTPUT_DIR


Examples of contents:
- Heightmap BMP previews
- Terrain layer visualizations
- Temporary inspection files

This directory:
- Is never consumed by automation
- Can be safely deleted at any time
- Exists purely for developer understanding

---

## Environment File Usage

A single `.env` file at the repository root controls all debug behavior:



RTSColonyTerrainGenerator/.env


Each module loads this file at runtime.

### Why `.env`?

- Avoids flag explosion
- Allows consistent debug behavior across tools
- Keeps scripts deterministic and clean
- Enables easy toggling without code edits

---

## Heightmap Debug Flags

### `MAPGEN_DEBUG_HEIGHTMAP_BMP`



MAPGEN_DEBUG_HEIGHTMAP_BMP=1


When enabled, the heightmap engine writes:

- Grayscale BMP
- One pixel per cell
- Pixel value = normalized height (0–255)

Use this to:
- Validate fault-line output
- Spot flat maps
- Understand elevation distribution

---

### `MAPGEN_DEBUG_LAYER_BMP`



MAPGEN_DEBUG_LAYER_BMP=1


When enabled, the heightmap engine writes:

- Color-coded BMP
- Each pixel represents a terrain layer

Current color mapping:
- Water → Blue
- Land → Green
- Pine Mountain → Dark Green
- Rock Mountain → Gray

Use this to:
- Validate classification thresholds
- Spot terrain boundary issues
- Confirm biome separation

---

## Safety Rules (Important)

- Debug output MUST NOT be written to `outbox/`
- Automation must never read from `debug/`
- `.env` must not change pipeline semantics
- Debug output must always be optional

If a debug feature changes automation behavior, it is a bug.

---

## Future Extensions

This system is intentionally extensible.

Planned or possible additions:
- Debug river overlays
- Pathfinding heatmaps
- Erosion pass visualizations
- Per-stage timing reports

All future debug output must follow the same rule:
**human-visible, automation-ignored**.

---

## Summary

| Area            | Owner     |
|-----------------|-----------|
| inbox/outbox    | machine   |
| archive/failed  | machine   |
| debug/          | human     |
| .env            | human     |

This separation keeps the pipeline honest, reproducible,
and scalable.

### HEIGHTMAP_FAULT_ITERATIONS

Controls how many fault-line iterations are applied during
heightmap generation.

- Higher values produce more rugged, mountainous terrain
- Lower values produce flatter, smoother maps

This setting is intended for **developer tuning** and is
read from `.env` by the heightmap worker.

Default: 50
