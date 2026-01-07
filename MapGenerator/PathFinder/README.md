# Trade & Connectivity Simulation

## Overview

This module evaluates whether all settlements in the world are reachable via land-based traversal.

It simulates a neutral "Trader" attempting to travel between every pair of settlements using the terrain produced by WorldFeatures.

The result is a **connectivity graph** and a set of **infrastructure requirements**.

---

## Pipeline Position

```
Heightmap
↓
Tiler
↓
WorldFeatures (natural terrain only)
↓
Trade & Connectivity Simulation ← YOU ARE HERE
↓
Pathfinder / Infrastructure Builder
↓
Gameplay Systems
```


---

## Inputs

### Required Inputs

- Heightmap (read-only)
- Terrain layers (biomes, water, cliffs, forests)
- WorldFeatures output:
  - Rivers
  - Mountains
  - Passes
  - Forest density
  - Marsh / swamp regions
- Settlement list:
  - Position
  - Type (village, town, city)
  - Civilization ID

### Assumptions

- Settlements already exist
- Terrain is finalized
- No artificial infrastructure exists yet

---

## Core Simulation Steps

### 1. Settlement Pair Analysis

For each settlement:
- Attempt to reach every other settlement
- Use land-based traversal only

This produces:
- Reachable paths
- Unreachable pairs
- Traversal cost metrics

---

### 2. Path Viability Evaluation

Each attempted path evaluates:
- Elevation changes
- Slope limits
- Water crossings
- Forest density
- Marsh traversal penalties
- Cliff impassability

Outcomes:
- Directly reachable
- Reachable with infrastructure
- Unreachable

---

### 3. Infrastructure Requests (Not Construction)

If a path fails, the system may request:

- Forest clearing
- Path creation
- Road creation
- Bridge placement
- Mountain pass carving (only at natural weak points)

This module **does not build** infrastructure.
It only emits **requests**.

---

### 4. Connectivity Graph Generation

Outputs a graph where:
- Nodes = settlements
- Edges = viable trade routes
- Edge weights = traversal cost

This graph becomes authoritative for:
- Trade simulation
- Diplomacy
- AI behavior
- Quest logic
- Lore generation

---

## Outputs

### Primary Output (Binary or Structured Data)

- Settlement connectivity graph
- Trade reachability flags
- Required infrastructure list

### Example Output Concepts

- Settlement A ↔ Settlement B: reachable (road suggested)
- Settlement C: isolated (mountain-locked)
- Settlement D: reachable only by bridge
- Settlement E: reachable but high-cost (marsh crossing)

---

## Deterministic Rules

- Same seed = same graph
- Same terrain = same failures
- No randomness after input freeze

---

## Failure Modes (Valid Outcomes)

The following are **acceptable and expected**:

- Isolated settlements
- Trade bottlenecks
- Single-path choke points
- High-cost routes
- Dangerous but viable paths

These create:
- Strategic gameplay
- Natural conflict zones
- Meaningful infrastructure investment

---

## Why the Trader Is “Dead”

The Trader is a **historical abstraction**.

Think of this system as:
> “The ghost of trade past tested this world.”

The paths it discovers:
- Become ancient roads
- Inform future development
- Shape civilization growth

The trader does not exist in gameplay — only the consequences do.

---

## Extension Hooks (Future)

This module is intentionally minimal.

Future systems may:
- Upgrade roads over time
- Add naval trade
- Introduce caravan ambushes
- Simulate seasonal path closures
- Attach lore to trade routes

None of that belongs here.

---

## Summary

If civilization exists,
and trade is possible,
then paths must exist.

If paths do not exist,
the world must change.

This module ensures the world earns its civilization.
