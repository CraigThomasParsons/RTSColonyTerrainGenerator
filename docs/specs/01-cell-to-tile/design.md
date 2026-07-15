# Design: 01-cell-to-tile

<!-- Lifecycle steps 3, 5, and 6: bounded context and domain model, Dafny strategy, CQRS design. -->

## Bounded Context

**Tile Resolution** owns this rule. It is the context whose language is the mapping
from cell space to tile space; Terrain Generation produces cells but has no concept
of a tile, and Pipeline Lifecycle moves artifacts between lanes without knowing what
is inside them. Putting the rule anywhere else would smear tile vocabulary across a
boundary that does not speak it. (Context list: CONTEXT.md and
`mapgen-spec-driven-planning/05-bounded-contexts-and-ownership.md`.)

## Domain Model

```text
Bounded Context: Tile Resolution
Domain Service / Aggregate: CellExpander
Inputs: CellCoordinate, CellMapDimensions
Output: TileRegion (an ordered sequence of four TileCoordinates)
Invariant: one valid cell owns exactly the four unique in-bounds tiles of its
           2×2 region, in the order TL, TR, BL, BR
```

Value objects in `MapGen.Domain`:

- `CellCoordinate` — zero-based `(x, y)` in cell space.
- `CellMapDimensions` — width and height in cells; construction rejects
  non-positive values.
- `TileCoordinate` — zero-based `(x, y)` in tile space.
- `TileMapDimensions` — width and height in tiles; derived as exactly double the
  cell map dimensions, never supplied independently.
- `TileRegion` — the four tiles belonging to one cell, ordered.

All terms already exist in CONTEXT.md (Cell, Tile, Cell-to-Tile Expansion) and the
charter's ubiquitous-language table; this slice introduces no new vocabulary.

## Dafny Strategy

**Level B — verified reference**, integration pattern: independent model that the C#
implementation must agree with (dual-reference design, ADR 0002). The file is
`specs/tiling/CellToTile.dfy`, carrying the function `ExpandCell` and one lemma per
postcondition:

- `ExpandCellProducesExactlyFour` — result length is four.
- `ExpandCellCoordinatesAreUnique` — no duplicates.
- `ExpandCellStaysInTileBounds` — every tile inside `(width×2, height×2)`.
- `ExpandCellEmitsTheContractualCorners` — the exact coordinates, in the
  contractual order.
- `TileMapWidth` / `TileMapHeight` — doubled dimensions are definitional, and the
  in-bounds lemma is proved against them.

Determinism needs no lemma: Dafny functions are pure, so identical inputs yield the
identical ordered result by construction — the strongest statement available.

Why this rule earns formal treatment: it is the canonical correctness-critical rule
of the Tile Resolution context (every downstream tile depends on it), and it is the
programme's chosen proving ground for the Dafny lane. Verification findings are
recorded in `verification-report.md` in this directory once the verification run
lands.

## CQRS Design

One command, no query, no events, no persistence (charter: a query such as
`GetResolvedTileRegion` arrives only when a tile-map artifact is persisted).

```csharp
public sealed record ResolveTileRegionCommand(
    CellCoordinate Cell,
    CellMapDimensions Dimensions);
```

The handler lives in `MapGen.Application`. Its whole job is: validate the request
(preconditions from `requirements.md`), call `CellExpander`, return the resulting
`TileRegion` — or a typed failure naming the violated precondition for an
out-of-bounds cell or invalid dimensions. The handler orchestrates; it does not
reproduce the expansion arithmetic.

A minimal `MapGen.Cli` project exposes the command as `expand-cell`, giving the BDD
`net` profile a process-level entry point. The CLI is a thin shell over the
handler — parsing arguments in, printing the region or failure out.

## Legacy Adapter Boundary

Legacy identification: the rule lives in
`MapGenerator/Tiler/Processing/TileIdResolver.cs` lines 85–96, which per cell emits
the tile id into TL `(2x, 2y)`, TR `(2x+1, 2y)`, BL `(2x, 2y+1)`, BR
`(2x+1, 2y+1)`. The charter's order equals the legacy order, so **order is
contractual**.

The boundary for this slice is the BDD profile seam, not a production interface: the
Gherkin steps speak only the domain language ("expand the cell at 3,4"), and the
profile chooses the adapter.

- **`legacy` profile adapter**: the legacy stage has no per-cell request surface, so
  the adapter synthesizes a 10×10 `.heightmap` in which only the target cell carries
  a distinctive terrain value, runs the prebuilt binary
  `MapGenerator/Tiler/bin/published/Tiler` (usage: `Tiler <heightmap>`, writing
  `./outbox/<id>.maptiles` relative to the working directory), and reads the tile
  region back out of the `.maptiles` — the legacy tile id is `terrain << 8 | mask`,
  so exactly the four tiles carrying that terrain byte are the cell's region.
- **`net` profile adapter**: invokes `MapGen.Cli expand-cell` and parses its output.

No production code knows which implementation is active; the application layer never
references the legacy stage. When a later slice replaces the Tiler stage itself, the
verified C# implementation slots in behind the stage contract, not behind this test
seam.

## Architectural Rules and Enforcement

Every rule names its enforcement path; a rule without one is a wish.

| Rule | Enforcement path |
|---|---|
| `MapGen.Domain` has no infrastructure dependency; dependencies point inward (Cli → Application → Domain, never the reverse) | `tests/MapGen.ArchitectureTests` |
| Postconditions: exactly four, unique, in-bounds, exact corners, doubled dimensions | `specs/tiling/CellToTile.dfy` lemmas + FsCheck properties in `tests/MapGen.Domain.Tests` |
| Coordinate order TL, TR, BL, BR is contractual | `ExpandCellEmitsTheContractualCorners` lemma + ordered-table assertions in the Gherkin scenarios on both profiles |
| Determinism: identical inputs, identical ordered result | Structural in the Verified Model (pure function) + FsCheck repeat-call property in `tests/MapGen.Domain.Tests` |
| Behaviour parity: same Gherkin green on `legacy` and `net` | cucumber-js profiles (`npm run bdd:legacy`, `npm run bdd:net`) |
| Compatibility with the legacy baseline | `tests/MapGen.CompatibilityTests` (golden-job dimension doubling) + the BDD legacy adapter (per-cell evidence against the real binary) |
| Invalid input is a typed failure at the command boundary, never a throw-through or silent clamp | Unit tests for the handler in `tests/MapGen.Domain.Tests` + the `@net-only` rejection scenario |
| Handlers orchestrate and do not reproduce domain arithmetic | Review checklist in the closing PR (no automated proxy exists for this yet) |

## Trade-offs, Non-Goals, and Risks

- **Order vs. set comparison** — the charter allowed treating the region as a set if
  the legacy order differed. It does not differ, so we chose the stronger contract:
  ordered comparison everywhere. Loosening it later would be a Specification
  correction.
- **Rejection is `@net-only`** — the legacy stage cannot be asked to expand one cell,
  so the rejection scenario proves the new command boundary only. This is an
  approved asymmetry, documented here and in `acceptance.md`, not a gap discovered
  later.
- **The CLI is a test seam, not the future stage entry point** — `MapGen.Cli
  expand-cell` exists for the BDD lane. Non-goal: designing the eventual C# Tiler
  stage executable in this slice.
- **Terrain-byte marker technique** — the legacy adapter identifies the region via a
  distinctive terrain value in the high byte of the tile id. Risk: it assumes the
  mask (low byte) never collides with the terrain byte, which holds because the
  layers occupy disjoint byte positions. If a future legacy change repacked the tile
  id, the adapter would fail loudly (wrong tile count), not silently.
- **Legacy binary writes relative to CWD** — the adapter must run the binary from a
  scratch working directory per scenario, or parallel scenarios would share an
  `outbox/`. Mitigated in the adapter, noted as a risk because it is easy to
  regress.
- **Not solved here** — tile id composition, adjacency masks, `.maptiles`
  serialization in new code, and replacement of the Tiler stage. Each is a later
  slice.
