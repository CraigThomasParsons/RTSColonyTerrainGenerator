# Requirements: 01-cell-to-tile

<!-- Lifecycle steps 1, 2, and 4: product requirement, BDD scenarios, domain contract. -->

Slice: Verified Cell-to-Tile Expansion — Gitea issue #7, milestone M3, tag
`@slice-01-cell-to-tile`. Charter:
`mapgen-spec-driven-planning/08-first-epic-verified-cell-to-tile.md`.

## Problem

Every stage downstream of Tiler — TreePlanter onward, through to the final 64×64
map-document payload — speaks in Tiles, and every Tile exists because the Cell-to-Tile
Expansion rule put it there. Today that rule lives only inside the legacy Tiler's
resolver loop, unnamed and untestable in isolation. If migration gets this rule wrong,
every tile the new pipeline emits is wrong, and the Level Designer receives a world
that silently disagrees with the legacy baseline.

This is also the programme's first Slice: it exists to prove the full lifecycle
(requirement → BDD → contract → Dafny → C# → tests → promotion) on a rule small enough
to hold in one head.

## Desired Behaviour

Cell-to-Tile Expansion (see CONTEXT.md): one Cell at zero-based coordinate `(x, y)`
inside the Cell Map Dimensions produces exactly the four unique Tile Coordinates of
its 2×2 Tile Region, all inside a tile map of `width×2` by `height×2`, in the agreed
order:

```text
(x × 2,     y × 2)      TL
(x × 2 + 1, y × 2)      TR
(x × 2,     y × 2 + 1)  BL
(x × 2 + 1, y × 2 + 1)  BR
```

Concretely: in a 10×10 cell map, cell `(3, 4)` produces `(6, 8)`, `(7, 8)`, `(6, 9)`,
`(7, 9)`. A cell outside the cell map — for example `(10, 9)` in a 10×10 map — is
rejected with a typed failure, not expanded.

## Business or Design Value

The rule is the load-bearing joint between cell space and tile space; proving it
correct once protects every downstream stage. Equally, this slice buys the process:
project structure, CI gates, dual-profile BDD, and review habits that all later
slices reuse.

## Scope

- The pure expansion rule as a domain service (`CellExpander`) with its value objects
  in `MapGen.Domain` (bounded context: Tile Resolution).
- A command boundary: `ResolveTileRegionCommand` and its handler in
  `MapGen.Application`, including rejection of out-of-bounds cells.
- A minimal `MapGen.Cli` exposing `expand-cell` as the `net`-profile entry point for
  the BDD lane.
- The Verified Model: `specs/tiling/CellToTile.dfy` (Level B verified reference).
- Dual-profile BDD for the charter's four scenarios; unit, property, architecture,
  and compatibility evidence.

## Out of Scope

- Tile identifier composition (`terrain << 8 | mask`) and adjacency-mask derivation —
  those stay in the legacy Tiler and get their own slices.
- Writing or reading `.maptiles` artifacts in the new code (the BDD legacy adapter
  parses them as evidence; production C# does not touch them here).
- Replacing the Tiler stage, its lanes, or its systemd wiring.
- Persistence and queries — no `GetResolvedTileRegion` until a tile-map artifact is
  persisted by new code.

## Legacy Baseline Behaviour

The legacy pipeline's Tiler stage defines current behaviour. The rule lives in
`MapGenerator/Tiler/Processing/TileIdResolver.cs` lines 85–96, which emits, per cell,
the same tile id into TL `(2x, 2y)`, TR `(2x+1, 2y)`, BL `(2x, 2y+1)`,
BR `(2x+1, 2y+1)`. The charter's coordinate order equals the legacy order, so order
is contract, not accident.

Golden Job fixtures under `tests/fixtures/golden/` (jobs
`43860dcf-6469-42a7-9843-4e33abeacfac`, `3c96b74c-6f86-4d27-a0ca-c567f385ae8e`,
`0860a05a-a410-4cc2-987d-a48a4cd120c7`) capture the baseline: 64×64-cell inputs
produced 128×128-tile `.maptiles`, demonstrating the dimension-doubling consequence
of the rule end to end.

Known quirk to preserve, not fix: the legacy stage has no per-cell request surface —
it expands whole maps — so it cannot exhibit rejection of a single out-of-bounds
cell. Rejection is a property of the new command boundary (see the `@net-only`
scenario below).

## BDD Scenarios

Feature file: `tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature`
(tag `@slice-01-cell-to-tile`), updated in this slice to the charter's four
scenarios:

1. **Expand the origin cell** — cell `(0, 0)` in a 10×10 cell map yields exactly the
   four coordinates `(0,0) (1,0) (0,1) (1,1)`.
2. **Expand an interior cell** — cell `(3, 4)` yields `(6,8) (7,8) (6,9) (7,9)`.
3. **Expand the final valid cell** — cell `(9, 9)` yields coordinates all inside a
   20×20 tile map.
4. **Reject an out of bounds cell** — cell `(10, 9)` fails because the cell
   coordinate is outside the cell map. Tagged `@net-only`: an approved, documented
   profile asymmetry (see Legacy Baseline Behaviour above).

Scenarios 1–3 must be green on both the `legacy` and `net` profiles from the same
Gherkin. The scenarios state the domain rule directly in CONTEXT.md vocabulary; no
Persona acts in them because no operator intent is involved — this is the pipeline's
arithmetic, not a workflow. The Persona-bearing scenarios remain in
`tests/bdd/features/00-cross-cutting/`.

## Domain Contract

The framework-free contract that `specs/tiling/CellToTile.dfy` and the
`MapGen.Domain` types both encode. Weakening any line below is a Specification
correction requiring human review.

### Preconditions

- Cell map width is greater than zero.
- Cell map height is greater than zero.
- Cell `x` is less than the cell map width.
- Cell `y` is less than the cell map height.

(Coordinates and dimensions are zero-based, confirmed in the charter.)

### Postconditions

- The result contains exactly four tile coordinates.
- All four coordinates are unique.
- Every coordinate is inside the tile map of `(width × 2, height × 2)`.
- The coordinates are, in order:

```text
(x × 2,     y × 2)
(x × 2 + 1, y × 2)
(x × 2,     y × 2 + 1)
(x × 2 + 1, y × 2 + 1)
```

### Invariants

- Tile Map Dimensions are exactly double the Cell Map Dimensions in each axis.
- The coordinate order TL, TR, BL, BR is contractual (it equals the legacy emission
  order); the result is an ordered sequence, not a set.
- The region's extrema are `min x = 2x`, `max x = 2x + 1`, `min y = 2y`,
  `max y = 2y + 1`.

### Failure Modes

- A cell coordinate at or beyond the cell map bounds, or non-positive dimensions, is
  rejected at the command boundary with a typed failure naming the violated
  precondition. No exception-as-control-flow, no silent clamping, no empty region.

### Determinism and Idempotency

Deterministic: identical inputs produce an identical ordered result — structurally
guaranteed in the Verified Model (Dafny functions are pure) and property-tested in
C#. Idempotency does not apply: the operation is a pure function with no state to
re-apply.

## Acceptance Summary

- [ ] The four charter scenarios exist in the feature file; scenarios 1–3 are green
      on the `legacy` profile and all four on the `net` profile.
- [ ] `specs/tiling/CellToTile.dfy` verifies: exactly-four, uniqueness, in-bounds,
      exact corner coordinates, and doubled dimensions are discharged lemmas.
- [ ] Unit and FsCheck property tests in `tests/MapGen.Domain.Tests` cover the
      charter's test plan (boundary cells plus generated valid inputs) and pass.
- [ ] `MapGen.Domain` has no infrastructure dependency (architecture tests pass).
- [ ] Compatibility with the legacy pipeline is demonstrated per
      `acceptance.md` (golden-job dimension doubling + per-cell evidence against the
      real legacy binary), with the `@net-only` asymmetry documented.
- [ ] `just quality` is green and the slice tag is appended to both promotion
      ledgers in the closing PR.
