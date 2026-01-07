# WeatherAnalyses — Context

## Purpose of This Document

This `context.md` file exists to anchor **WeatherAnalyses** as an engine-level pipeline stage.
It defines *why this stage exists*, *what it is allowed to do*, and *how it must behave* relative to the rest of the MapGenerator pipeline.

This document should be read **before** any other design or implementation files in this directory.

---

## Position in the Pipeline

WeatherAnalyses sits *after* Heightmap generation and *before* any system that makes world decisions.

```text
Heightmap (geometry, locked)
  ↓
WeatherAnalyses (interpretation, read-only)
  ↓
Tiler / TreePlanter / WorldFeatures (decisions & actions)
```

### Immutable Boundary

* Heightmap is **feature-complete and locked**
* WeatherAnalyses **must never mutate** the heightmap
* Downstream stages **must not re-interpret geometry independently**

WeatherAnalyses is the **single source of analytical truth** derived from terrain.

---

## Conceptual Responsibility

WeatherAnalyses answers:

> "What does this terrain *mean*?"

It does **not** answer:

> "What should the terrain become?"

This distinction is critical.

### Allowed

WeatherAnalyses may:

* Read height values
* Compare neighboring elevations
* Compute gradients, flow, basins, ridges
* Predict where water *would* go
* Identify candidate features (passes, ramps, chokepoints)
* Output derived metadata layers

### Forbidden

WeatherAnalyses must NOT:

* Modify elevation values
* Carve rivers or lakes
* Flatten terrain
* Place tiles, trees, roads, or features
* Decide biomes
* Introduce randomness beyond deterministic analysis

---

## Mental Model

Think of WeatherAnalyses as a **GIS-style analysis pass** applied to a fantasy world.

* Cells = physical reality
* Heightmap = geometry
* WeatherAnalyses = interpretation
* WorldFeatures = intent & construction

Once WeatherAnalyses has run, downstream systems should **trust its output** instead of re-deriving terrain meaning ad hoc.

---

## Cell-Centric Design

WeatherAnalyses operates exclusively on **Cells**, not Tiles.

* A Cell represents a unit of terrain truth
* Each Cell later projects into 4 Tiles (2×2)
* Tiles are visual and replaceable

All WeatherAnalyses outputs:

* Are aligned to the Cell grid
* Share the same width/height as the heightmap
* Are safe to cache, reload, and re-project

---

## Determinism Contract

WeatherAnalyses must be fully deterministic.

Given the same heightmap input:

* Outputs must be byte-identical
* Results must not depend on thread order, timing, or platform
* Tie-breaks must be explicit

Design implications:

* Prefer integer or fixed-point math
* Avoid non-deterministic iteration orders
* Use stable sorting where ordering matters

---

## Output Philosophy

WeatherAnalyses produces **analytical layers**, not world edits.

Examples of layers:

* slope_magnitude
* slope_direction
* flow_direction
* flow_accumulation
* basin_id
* ridge_strength
* traversal_cost_hint

These layers are:

* Parallel grids
* Self-describing
* Stored in a single binary payload per job (preferred)

Downstream systems may:

* Read these layers
* Combine them with their own rules
* Ignore layers they do not need

They must NOT:

* Modify WeatherAnalyses output
* Treat WeatherAnalyses as advisory-only when terrain meaning is involved

---

## Terrain Semantics

The heightmap already defines terrain bands:

```text
0–79    → Water
80–159  → Land
160–219 → PineMountain
220+    → RockMountain
```

WeatherAnalyses must:

* Respect these bands
* Be edge-aware when analyzing transitions
* Avoid smoothing across semantic boundaries (especially cliffs)

This ensures:

* Beaches are detected correctly
* Cliffs remain sharp
* Mountain passes are meaningful

---

## Relationship to Weather

Despite the name, WeatherAnalyses does not simulate time-based weather.

Instead, it models **long-term terrain-driven tendencies**:

* Where water naturally flows
* Where erosion pressure exists
* Where ridges and valleys constrain movement

Short-term weather systems (rain, snow, seasons) may consume this data later, but are **out of scope** here.

---

## Extensibility Rule

New analytical layers may be added if and only if:

* They are derived solely from existing terrain data
* They do not require terrain mutation
* They are useful to at least one downstream system

WeatherAnalyses should grow by **adding layers**, not by changing meaning.

---

## Design Tone

This stage should be:

* Explicit
* Boring
* Correct
* Auditable

Clarity is more important than cleverness.

If a future reader asks:

> "Why does this exist?"

The answer should be obvious from the code and these documents.

---

## Summary

WeatherAnalyses is the interpretive spine of the world generator.

* Heightmap defines *shape*
* WeatherAnalyses defines *meaning*
* WorldFeatures defines *intent*

Breaking this separation will cause subtle, compounding bugs later.

Keeping it clean makes the world believable, extensible, and debuggable.
