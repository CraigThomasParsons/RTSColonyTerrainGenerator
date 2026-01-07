# WeatherAnalysesSpec.md

## Purpose

The **WeatherAnalyses** module performs **non-destructive environmental analysis** on generated terrain data.

It interprets terrain geometry and tiler semantics to derive **secondary environmental layers** such as slope, flow direction, and basin membership.

This module **never modifies the heightmap or tiles**.  
Instead, it produces a **parallel binary artifact** that downstream systems may consult.

---

## Position in the Pipeline



Heightmap
↓
Tiler
↓
WeatherAnalyses
↓
TreePlanter
↓
WorldFeatures


WeatherAnalyses is an **interpretation stage**, not a generation stage.

---

## Responsibilities

WeatherAnalyses is responsible for:

- Reading finalized terrain geometry
- Computing environmental derivatives
- Produing deterministic, reproducible analysis data
- Emitting a standalone binary file

It is **not responsible** for:

- Modifying height values
- Carving rivers
- Altering tiles
- Creating world features
- Making aesthetic decisions

---

## Inputs

### Required Inputs

| Source | Description |
|------|------------|
| Heightmap binary | Original terrain elevation data |
| Tiler metadata | Cell dimensions, adjacency, scale |

All inputs are treated as **read-only**.

---

## Outputs

### Primary Output

A single binary file, written to:



WeatherAnalyses/outbox/<job_id>.weather


This file contains **parallel grid-aligned environmental layers**.

---

## Binary Format Overview

### File Header

| Field | Type | Description |
|-----|-----|------------|
| magic | u32 | File identifier |
| version | u16 | Format version |
| width | u32 | Grid width in cells |
| height | u32 | Grid height in cells |
| layer_count | u16 | Number of layers included |

---

## Environmental Layers

Each layer covers the **entire grid** and aligns exactly with heightmap cells.

Layers are optional and versioned.

---

### Layer: Slope Map

**Purpose**  
Represents terrain steepness at each cell.

**Type**


i16 per cell


**Description**
- Derived from height differences between neighboring cells
- Normalized to engine scale
- Used for:
  - movement cost
  - erosion likelihood
  - vegetation filtering

---

### Layer: Flow Direction

**Purpose**  
Indicates where water would naturally flow from each cell.

**Type**


u8 per cell


**Encoding**


0 = no flow / local minimum
1 = north
2 = north-east
3 = east
4 = south-east
5 = south
6 = south-west
7 = west
8 = north-west


**Notes**
- Deterministic
- Single direction per cell
- Used for river routing and basin detection

---

### Layer: Basin ID

**Purpose**  
Identifies drainage basins and catchment areas.

**Type**


u32 per cell


**Description**
- Cells sharing the same basin ID ultimately drain to the same sink
- Basins may represent:
  - lakes
  - inland seas
  - ocean drains

---

### Layer: Erosion Potential (Optional)

**Purpose**  
Estimates how susceptible terrain is to erosion.

**Type**


u8 per cell


**Factors**
- slope
- flow accumulation
- local height variance

**Important**  
This layer **does not perform erosion** — it only reports likelihood.

---

### Layer: Wetness Index (Optional)

**Purpose**  
Represents long-term moisture accumulation.

**Type**


u8 per cell


**Usage**
- TreePlanter density rules
- Marsh detection
- Floodplain marking

---

## Determinism Rules

WeatherAnalyses **must be deterministic**.

Given:
- identical heightmap
- identical tiler metadata

The output **must be bit-identical**.

Random numbers are **not permitted**.

---

## Performance Expectations

- Cache-friendly grid traversal
- Linear memory access preferred
- No allocations inside inner loops
- One scratch buffer per pass maximum

---

## Failure Handling

If analysis fails:

- Job file moves to `failed/`
- Partial outputs are deleted
- Heightmap and tile data remain untouched

---

## Design Principles

1. Read-only inputs  
2. Write-only outputs  
3. No geometry mutation  
4. Grid alignment preserved  
5. Human-interpretable debugging layers  
6. Composable downstream usage  

---

## Downstream Usage Examples

### TreePlanter
- Avoids high slope
- Prefers wet basins
- Spawns riverbank vegetation

### WorldFeatures
- Draws rivers from flow direction
- Places bridges across basins
- Creates beaches at basin–ocean edges

---

## Future Extensions

WeatherAnalyses may later include:

- snowfall likelihood
- seasonal flooding
- wind exposure
- temperature bands

These **extend the analysis file**, never rewrite upstream artifacts.

---

## Summary

WeatherAnalyses is a **pure analysis pass** that enriches the world without destabilizing it.

It enables:
- richer worlds
- safer iteration
- future simulation layers
- stable saves

It is intentionally boring — and that is its greatest strength.
