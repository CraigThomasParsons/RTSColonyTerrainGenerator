# Design: 02-adjacency-mask

<!-- Lifecycle steps 3, 5, and 6: bounded context and domain model, Dafny strategy, CQRS design. -->

## Bounded Context

**Tile Resolution** owns this rule, the same context that owns Cell-to-Tile Expansion.
The adjacency mask is pure tile vocabulary — it is the tile's statement about its
neighbours — and it is derived entirely from terrain equality, which Tile Resolution
already reasons about. Terrain Generation produces the cells and their terrain layers
but has no concept of an adjacency mask; Pipeline Lifecycle moves the `.maptiles`
artifact between lanes without knowing what a mask means. Putting the rule anywhere
else would smear tile vocabulary across a boundary that does not speak it. (Context
list: CONTEXT.md and `mapgen-spec-driven-planning/05-bounded-contexts-and-ownership.md`.)

## Domain Model

```text
Bounded Context: Tile Resolution
Domain Service: AdjacencyMaskCalculator
Inputs: TerrainGrid, CellCoordinate (x, y)
Output: AdjacencyMask (a byte in [0, 15])
Invariant: a bit is set iff the orthogonal neighbour in that direction exists on the
           grid and shares the cell's terrain; adjacency is symmetric between pairs
```

Value objects in `MapGen.Domain` (Tile Resolution namespace):

- `TerrainGrid` — `width`, `height`, and `terrain[x, y]` (a terrain value per cell).
  Construction rejects non-positive dimensions. Terrain values are compared for
  equality; the grid places no upper bound on them.
- `AdjacencyMask` — a wrapper over a byte in `[0, 15]` with named `North`, `East`,
  `South`, `West` boolean accessors reading bits 0/1/2/3. Construction rejects values
  above 15.

Domain service:

- `AdjacencyMaskCalculator.ComputeMask(grid, x, y) -> AdjacencyMask` — the single-cell
  rule, the authoritative definition.
- `AdjacencyMaskCalculator.ComputeMasks(grid)` — the whole-grid convenience over
  `ComputeMask`, walking row-major to match the legacy order. Used by compatibility
  evidence; the command path needs only the single-cell form.

`CellCoordinate` is reused from Epic 1. `TerrainGrid` and `AdjacencyMask` are new
ubiquitous-language terms; they are added to CONTEXT.md in the same change if not
already present, using the definitions above.

## Dafny Strategy

**Level B — verified reference**, integration pattern: independent model that the C#
implementation must agree with (dual-reference design, ADR 0002). The file
`specs/tiling/AdjacencyMask.dfy` is **already authored and verifying — 15 proof
obligations, 0 errors**. It models a `Grid(width, height, terrain)`, the four guarded
bit functions (`NorthBit`, `EastBit`, `SouthBit`, `WestBit`), their sum `Mask`, and
these lemmas:

- `MaskInRange` — the mask is always in `[0, 15]`.
- `EdgeCellsNeverSetOffMapBits` — top row sets no North, left column no West, bottom
  row no South, right column no East.
- `EastWestSymmetry` — a cell's East bit is set exactly when the cell to its right has
  its West bit set.
- `NorthSouthSymmetry` — a cell's South bit is set exactly when the cell below has its
  North bit set.
- `BitsReflectNeighbourPredicate` — each bit is set exactly when its "neighbour exists
  and shares terrain" predicate holds.

Determinism needs no lemma: Dafny functions are pure, so identical inputs yield the
identical mask by construction — the strongest statement available, and the report
must say so rather than imply it was proved separately.

Why this rule earns formal treatment: it is a correctness-critical rule of the Tile
Resolution context (every downstream connectivity decision depends on it) and the
first rule in the programme with a relational invariant — symmetry between adjacent
cells — that examples alone cannot establish for all inputs. Verification findings are
recorded in `verification-report.md` in this directory, authored by the human reviewer
after the verification run (not alongside this spec pack).

## CQRS Design

One command, no query, no events, no persistence. Per ADR 0005 the command is
dispatched through Mediator: it implements `IRequest<Result<T>>`, its handler
implements `IRequestHandler<TRequest, Result<AdjacencyMask>>` with the async
`Handle(request, ct)` signature, and hosts resolve `ISender` rather than naming the
handler.

```csharp
public sealed record ComputeAdjacencyMaskCommand(
    TerrainGrid Grid,
    CellCoordinate Cell) : IRequest<Result<AdjacencyMask>>;
```

The handler lives in `MapGen.Application` and is registered by the existing
`AddMapGenApplication()` composition root (ADR 0005). Its whole job is: validate the
request (preconditions from `requirements.md`), call
`AdjacencyMaskCalculator.ComputeMask`, and return the resulting `AdjacencyMask` — or a
typed `Result` failure naming the violated precondition for an out-of-bounds cell or
invalid dimensions. The handler orchestrates; it does not reproduce the bit arithmetic.
Failures surface as `Result`, never as thrown exceptions.

A new `mask-cell` subcommand on `MapGen.Cli` gives the BDD `net` profile a
process-level entry point:

```text
mask-cell --width <w> --height <h> --x <x> --y <y> --terrain <csv>
```

`--terrain` is the grid in row-major order as a comma-separated list of small ints
(`width × height` values). The CLI parses arguments, builds the `TerrainGrid`, resolves
`ISender`, sends the command, and prints the mask (or the typed failure and a non-zero
exit). It is a thin shell over the handler.

## Legacy Adapter Boundary

Legacy identification: the rule lives in
`MapGenerator/Tiler/Processing/CellBitmaskCalculator.cs` (bit weights N=1, E=2, S=4,
W=8; guards `y>0`, `x+1<width`, `y+1<height`, `x>0`; row-major order). The mask is
packed into the tile-id low byte by `TileIdResolver.cs` (`terrain << 8 | mask`) and
written into all four tiles of the cell's 2×2 region.

The boundary for this slice is the BDD profile seam, not a production interface: the
Gherkin steps speak only the domain language ("the mask of the cell at 1,1"), and the
profile chooses the adapter.

- **`legacy` profile adapter**: synthesizes a small `.heightmap` with a chosen terrain
  layout (terrain values in `[0, 3]`), runs the prebuilt binary
  `MapGenerator/Tiler/bin/published/Tiler` (usage: `Tiler <heightmap>`, writing
  `./outbox/<id>.maptiles` relative to the working directory) from a per-scenario
  scratch directory, and reads the target cell's mask back as the **low nibble**
  (`id & 0x0F`) of any one of that cell's four 2×2 tiles — all four carry the same tile
  id, so any of them serves.
- **`net` profile adapter**: invokes `MapGen.Cli mask-cell` with the same grid and
  parses its output.

No production code knows which implementation is active; the application layer never
references the legacy stage. When a later slice replaces the Tiler stage itself, the
verified C# implementation slots in behind the stage contract, not behind this test
seam.

## Architectural Rules and Enforcement

Every rule names its enforcement path; a rule without one is a wish.

| Rule | Enforcement path |
|---|---|
| `MapGen.Domain` has no infrastructure dependency; dependencies point inward (Cli → Application → Domain, never the reverse) | `tests/MapGen.ArchitectureTests` |
| The `ComputeAdjacencyMaskCommand` handler is dispatched through Mediator (`IRequestHandler<,>`, `ISender`), per ADR 0005 | `Request_handlers_implement_the_mediator_handler_interface` architecture test + `MediatorWiringTests` in `MapGen.Application.Tests` |
| Mask is always in `[0, 15]` | `AdjacencyMask.dfy` `MaskInRange` lemma + FsCheck property in `tests/MapGen.Domain.Tests` |
| Each bit is set iff its neighbour exists and shares terrain | `AdjacencyMask.dfy` `BitsReflectNeighbourPredicate` lemma + FsCheck property |
| Edge cells never set off-map bits (corner `(0,0)` ≤ East\|South) | `AdjacencyMask.dfy` `EdgeCellsNeverSetOffMapBits` lemma + boundary unit tests |
| Adjacency is symmetric between orthogonally adjacent cells | `AdjacencyMask.dfy` `EastWestSymmetry` + `NorthSouthSymmetry` lemmas + FsCheck symmetry property + the symmetry Gherkin scenario on both profiles |
| Behaviour parity: same Gherkin green on `legacy` and `net` | cucumber-js profiles (`npm run bdd:legacy`, `npm run bdd:net`) |
| Compatibility with the legacy baseline (bit weights, guards, packing) | the BDD legacy nibble probe against the real binary (per-cell evidence) + the optional golden-recompute test in `tests/MapGen.CompatibilityTests` |
| Invalid input is a typed `Result` failure at the command boundary, never a throw-through or silent default mask | Handler unit tests in `tests/MapGen.Domain.Tests` + the `@net-only` rejection scenario |
| Handlers orchestrate and do not reproduce domain arithmetic | Review checklist in the closing PR (no automated proxy exists for this yet) |

## Trade-offs, Non-Goals, and Risks

- **Symmetry as invariant, not just example** — the charter could have settled for a
  handful of symmetric-pair examples. We chose the stronger contract: symmetry is
  proved for all interior pairs in the Verified Model and property-tested in C#, with
  one Gherkin scenario as the human-readable witness. Loosening it later would be a
  Specification correction.
- **Rejection is `@net-only`** — the legacy stage cannot be asked to mask one cell, so
  the rejection scenario proves the new command boundary only. This is an approved
  asymmetry, documented here and in `acceptance.md`, not a gap discovered later — the
  same pattern as Epic 1.
- **Terrain range asymmetry between profiles** — the legacy `HeightmapReader` accepts
  terrain `0..3`, so `legacy`-profile grids are bound to `[0, 3]`. The domain and the
  Verified Model compare terrain for equality with no upper bound. The shared
  scenarios stay in `[0, 3]` so both profiles run identical inputs; the wider domain
  range is exercised only by unit and property tests. Risk: a reviewer mistakes the
  `[0, 3]` scenario bound for a domain rule — called out in `requirements.md` and here
  to prevent that.
- **Mask read as the low nibble, via the packed tile id** — the legacy adapter reads
  `id & 0x0F` from a tile whose id is `terrain << 8 | mask`. This incidentally depends
  on tile-id packing (a later slice's rule), but only as an observation channel, not as
  a claim about packing. If a future legacy change repacked the id, the probe would
  read a wrong nibble and the scenario would fail loudly, not silently.
- **The CLI is a test seam, not the future stage entry point** — `MapGen.Cli
  mask-cell` exists for the BDD lane. Non-goal: designing the eventual C# Tiler stage
  executable in this slice.
- **Legacy binary writes relative to CWD** — the adapter must run the binary from a
  scratch working directory per scenario, or parallel scenarios would share an
  `outbox/`. Reused from Epic 1's adapter; noted because it is easy to regress.
- **Not solved here** — tile-id composition as a rule of new code, `.maptiles`
  serialization in new code, diagonal/8-neighbour masks, and replacement of the Tiler
  stage. Each is a later slice or explicitly out of scope.
