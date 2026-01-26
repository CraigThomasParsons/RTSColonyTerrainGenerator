# WorldCartridge (WCAR) — Context

## What This Is

WorldCartridge (.wcar) is a binary, chunk-based container format that represents
a fully generated game world as a sealed, portable artifact.

It is the canonical output of the MapGenerator pipeline.

WCAR is not a map file.
WCAR is not an engine format.
WCAR is not a save game.

It is a **world in a box**.

## Core Philosophy

• Deterministic
• Immutable
• Inspectable
• Engine-agnostic at the core
• Engine-compatible at the edges

WCAR preserves semantic intent.
Engines consume projections.

## Execution Model

WCAR → CHK → Stratagus → simulation

StarCraft-compatible CHK maps are embedded as executable projections.
They are derived from WCAR data and may lose information.
WCAR remains the source of truth.

## Why Stratagus

Stratagus provides:
• A real RTS engine
• Open source codebase
• Headless execution capability
• StarCraft-compatible map loading

This allows WCAR artifacts to be validated through actual gameplay simulation.

## Long-Term Direction

• Autonomous world validation
• AI-driven regression testing
• Multi-engine projection (future)
• World diffing and analysis

This system is intentionally designed to scale in capability without
requiring format-breaking changes.
