# Tiler

Tile generation service for breaking terrain into manageable chunks.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming tiling requests
- `outbox/` - Generated tile files
- `archive/` - Archived processed tiles

## Tiler implementation plan that is:

- deterministic
- engine-agnostic
- compatible with future Stitcher / WFC
- simple enough to implement without regret
- explicit enough to never rot
- No new features, no creativity, no scope creep.

## Tiler Implementation Plan

(Heightmap → Tile Artifact)

0️⃣ Tiler’s Single Responsibility (re-stated)

Interpret authoritative terrain truth and emit a fully resolved visual tile map.

Nothing more. Nothing less.

1️⃣ Executable Shape (CLI-first)

The Tiler is a pure batch processor.

Invocation
tiler \
  MapGenerator/Heightmap/outbox/map_00042.heightmap \
  MapGenerator/Tiler/outbox/

Guarantees

No global state

No temp files outside outbox

No randomness

Same input → same output (byte-for-byte)

2️⃣ Internal Pipeline (deterministic stages)

The Tiler should be written as linear, explicit stages.

Stage 1: Read heightmap file
Stage 2: Build cell grid
Stage 3: Compute cell bitmasks
Stage 4: Resolve tile IDs
Stage 5: Emit tile artifact(s)
Stage 6: (Optional) Emit debug artifacts


Each stage consumes immutable data and produces new immutable data.

3️⃣ Data Structures (authoritative, minimal)
3.1 Cell grid (input truth)
struct Cell
{
    byte Height;        // 0–255 (unused by tiler logic for now)
    byte TerrainLayer;  // 0..3 authoritative enum
}


Stored as:

Cell[width, height]


Row-major, origin convention frozen once and documented.

3.2 Bitmask grid (derived, pure)
// 4-bit mask: N E S W
byte CellMask; // 0..15


Stored as:

byte[width, height]


Rules:

Calculated once

Never modified

No diagonals at this stage

3.3 Tile output grid (final truth)

Each cell produces exactly 4 tiles.

Tile grid size:

tile_width  = cell_width  * 2
tile_height = cell_height * 2


Tile record:

struct Tile
{
    ushort TileId;   // resolved, final
}


No terrain type stored here — that belongs to cells.

4️⃣ Bitmask Computation (locked behavior)
4.1 Neighbor inspection

For each cell (x, y):

Direction	Offset
North	(0, -1)
East	(+1, 0)
South	(0, +1)
West	(-1, 0)

Matching rule (absolute):

neighbor.terrain_layer == cell.terrain_layer


Out-of-bounds neighbors are NON-MATCHING.

4.2 Mask encoding (pure)
Bit 0 (1)  = North
Bit 1 (2)  = East
Bit 2 (4)  = South
Bit 3 (8)  = West


Result:

mask ∈ [0, 15]


No branching by terrain type.

5️⃣ Tile ID Resolution (table-driven)
5.1 Tileset base IDs (example)

These are constants, not magic numbers:

WATER_BASE         = 0x0000
LAND_BASE          = 0x0100
PINE_MOUNTAIN_BASE = 0x0200
ROCK_MOUNTAIN_BASE = 0x0300


(Exact values TBD once you lock tile counts.)

5.2 Tile ID formula
tile_id = TERRAIN_BASE + mask


This guarantees:

stable IDs

deterministic expansion

no cross-terrain bleed

trivial WFC adjacency extraction later

No switch statements required.

6️⃣ Applying Cell → 2×2 Tiles
6.1 Default rule (current scope)

Each of the 4 tiles emitted for a cell receives the same tile ID.

TL | TR
------
BL | BR


All four identical.

This keeps:

logic simple

determinism absolute

future refinement possible without invalidating data

6.2 Optional future refinement (explicitly deferred)

You already scoped this correctly:

diagonal smoothing

shoreline cuts

sub-tile beveling

These must:

use only existing cell mask data

never affect determinism

never change cell authority

Not implemented now.

7️⃣ Output Artifacts (versioned, inspectable)
7.1 Primary artifact (production)

Binary tile map (recommended)

Header:
- u32 tile_width
- u32 tile_height
- u64 deterministic_seed
- u32 tiler_version

Body:
- u16[tile_width * tile_height] tile_ids (row-major)


Why binary:

compact

fast

engine-friendly

immutable

7.2 Optional debug artifacts (never consumed)

All optional, never read by other stages.

A) Mask dump (human-readable)
13 15 15  7
12 15 15  6
 8 14 14  4

B) HTML grid

cell grid

colored by terrain

mask number overlaid

borders reflect N/E/S/W mismatches

This is excellent for sanity checks.

8️⃣ Determinism Enforcement Checklist

The Tiler must:

avoid iteration-order side effects

never hash unordered collections

never use system time

never use RNG

never parallelize without strict ordering

If multithreading is ever added:

masks must be computed first

tile emission must be deterministic in order

9️⃣ Compatibility with Stitcher / WFC (future-proofing)

By design, you now have:

explicit adjacency (mask bits)

terrain-separated tilesets

stable tile IDs

no procedural noise baked in

This makes future systems trivial:

Stitcher

matches tiles by compatible masks

stitches borders without re-tiling

WFC

adjacency rules derived directly from (tile_id, direction)

entropy calculation trivial

no reclassification needed

You are not locking yourself into WFC — you’re making it possible.

Let’s lock tile ID ranges cleanly and permanently.

I’m going to give you a scheme that is:

 - deterministic

 - compact

 - future-proof

 - WFC-friendly

 - backward-compatible with everything you’ve specified

Once this is locked, it should never change, even 10 years from now.
---
### 🔒 Locked Tile ID Range Specification
### 1️⃣ Design Goals (why this looks the way it does)

Tile IDs must:

- Encode terrain type

- Encode bitmask variant

- Be resolvable with simple arithmetic

- Leave headroom for future tilesets

- Be stable across versions

Your rule:

(tile_set_id, mask) → tile_id

We will formalize that.

# Tiler — Cell Bitmask Processing

The **Tiler** stage converts authoritative heightmap cell data into a fully
resolved tile map suitable for direct use by the game engine and future
stitching / WFC tooling.

This stage is **purely interpretive**:
- No randomness
- No terrain modification
- No procedural generation
- Deterministic output only

---

## Pipeline Position

Heightmap → Tiler → (future stages)

yaml
Copy code

The Tiler consumes `.heightmap` files from its `inbox/`, which is a symlink to
the Heightmap stage `outbox/`.

---

## Cell → Tile Model

- The Heightmap operates in **cells**
- Each cell is authoritative for terrain classification
- Each cell produces **4 tiles (2×2)**
- Tiles are visual representations only

The Tiler never invents terrain features.

---

## Bitmasking Overview

The Tiler computes a **4-bit adjacency mask per cell** based on terrain layer
equality with its cardinal neighbors.

### Neighbor Directions

| Direction | Bit | Value | Offset |
|---------|----|------|--------|
| North | Bit 0 | 1 | (0, −1) |
| East  | Bit 1 | 2 | (+1, 0) |
| South | Bit 2 | 4 | (0, +1) |
| West  | Bit 3 | 8 | (−1, 0) |

A bit is set **if and only if** the neighboring cell exists **and** has the same
terrain layer.

Out-of-bounds neighbors are treated as **non-matching**.

---

## Mask Range

mask ∈ [0..15]

yaml
Copy code

Examples:

- `0`   → isolated cell
- `15`  → fully surrounded by same terrain
- other values → edges, corners, peninsulas

---

## Determinism Guarantee

For the same:
- `.heightmap` input
- Tiler version

The computed masks and emitted tile artifacts are **byte-for-byte identical**.

Execution order, platform, and threading do not affect output.

---

## Sample Mask Output (Debug)

4 2 14 14 14
7 12 3 11 15
7 15 14 12 3
7 15 15 15 14
7 15 15 15 15

yaml
Copy code

This shows:
- Lower mask values at edges
- Higher values in contiguous regions
- Correct transitions between terrain regions

---

## Tile ID Resolution (Next Stage)

Each tile ID is resolved using:

tile_id = (terrain_layer << 8) | mask

yaml
Copy code

Each terrain owns a 256-ID block, guaranteeing:
- No cross-terrain bleed
- Stable IDs
- Future expansion space

---

## Output

The Tiler emits a `.maptiles` binary artifact containing:
- A fixed header
- A row-major grid of resolved tile IDs (`u16`)

The output is fully resolved and requires **zero runtime logic** to render.

---
PART 2 — 🧱 Implement .maptiles Binary Writer
Now we implement the final emission step.

This writes the locked binary tile artifact format you already approved.

File location
Create:

swift
Copy code
MapGenerator/Tiler/IO/MapTilesWriter.cs
IO/MapTilesWriter.cs
csharp
Copy code
using System;
using System.IO;
using Tiler.Model;

namespace Tiler.IO
{
    /// <summary>
    /// Writes resolved tile data to a .maptiles binary artifact.
    ///
    /// This file is the FINAL output of the Tiler stage.
    /// It contains fully resolved tile IDs and requires no
    /// post-processing by the game engine.
    ///
    /// Binary format (little-endian):
    ///
    /// Header (32 bytes):
    ///   char[4]  magic           ("MTIL")
    ///   u32      version         (currently 1)
    ///   u32      tile_width
    ///   u32      tile_height
    ///   u64      deterministic_seed
    ///   u32      tile_count
    ///   u32      reserved        (must be 0)
    ///
    /// Body:
    ///   u16[tile_count] tile_ids (row-major)
    /// </summary>
    public static class MapTilesWriter
    {
        /// <summary>
        /// Writes a .maptiles file to disk.
        ///
        /// Determinism:
        /// - Given the same tile IDs and metadata, output bytes
        ///   are identical on every run.
        /// </summary>
        /// <param name="outputPath">Destination file path.</param>
        /// <param name="tileIds">
        /// Fully resolved tile ID grid indexed as [x, y].
        /// </param>
        /// <param name="deterministicSeed">
        /// Seed copied from the heightmap for provenance.
        /// </param>
        public static void Write(
            string outputPath,
            ushort[,] tileIds,
            ulong deterministicSeed)
        {
            if (tileIds == null)
                throw new ArgumentNullException(nameof(tileIds));

            uint tileWidth = (uint)tileIds.GetLength(0);
            uint tileHeight = (uint)tileIds.GetLength(1);

            if (tileWidth == 0 || tileHeight == 0)
                throw new ArgumentException("Tile grid must be non-empty.");

            uint tileCount = tileWidth * tileHeight;

            using FileStream stream = File.Create(outputPath);
            using BinaryWriter writer = new BinaryWriter(stream);

            // ---- Header ----

            // Magic: "MTIL"
            writer.Write(new[] { (byte)'M', (byte)'T', (byte)'I', (byte)'L' });

            // Version
            writer.Write((uint)1);

            // Dimensions
            writer.Write(tileWidth);
            writer.Write(tileHeight);

            // Deterministic seed
            writer.Write(deterministicSeed);

            // Tile count
            writer.Write(tileCount);

            // Reserved (must be zero)
            writer.Write((uint)0);

            // ---- Tile IDs (row-major) ----
            for (uint y = 0; y < tileHeight; y++)
            {
                for (uint x = 0; x < tileWidth; x++)
                {
                    writer.Write(tileIds[x, y]);
                }
            }
        }
    }
}
How this will be used (next wiring step)
Soon, Program.cs will:

Load .heightmap

Compute cell masks

Resolve tile IDs

Call MapTilesWriter.Write(...)

We have not skipped any steps or blurred responsibilities.

What you have now (major milestone)
✔ Heightmap reader
✔ Cell bitmask calculator
✔ Locked tile ID scheme
✔ Locked binary output format
✔ Binary writer implemented
✔ README documentation captured

This is real engine-grade terrain infrastructure.

