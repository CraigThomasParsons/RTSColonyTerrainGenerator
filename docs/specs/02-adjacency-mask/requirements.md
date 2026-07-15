# Requirements: 02-adjacency-mask

<!-- Lifecycle steps 1, 2, and 4: product requirement, BDD scenarios, domain contract. -->

Slice: Verified Adjacency-Mask Construction — Gitea issue #10, milestone M4, tag
`@slice-02-adjacency-mask`. Epic 2, building directly on Epic 1 (Verified
Cell-to-Tile Expansion, issue #7, `docs/specs/01-cell-to-tile/`) and on the merged
Mediator adoption (ADR 0005, `docs/adr/0005-mediator-in-application-layer.md`).

## Problem

Epic 1 proved where a cell's four tiles land. It did not prove what those tiles say
about their surroundings. Every tile the legacy Tiler emits carries a 4-bit adjacency
mask in the low byte of its tile id (`terrain << 8 | mask`), and TreePlanter onward —
through to the final 64×64 map-document payload — reads that mask to decide how a tile
connects to its neighbours. Today the rule lives only inside the legacy Tiler's
`CellBitmaskCalculator`, unnamed and untestable in isolation. If migration gets this
rule wrong, every tile edge the new pipeline draws is wrong, and the Level Designer
receives a world whose connectivity silently disagrees with the legacy baseline.

Epic 1 bought the process; Epic 2 is the first slice to run that process on a rule
with real neighbour structure — grid edges, terrain equality, and a symmetry the
Verified Model can state and prove.

## Desired Behaviour

Adjacency-Mask Construction: each Cell at zero-based coordinate `(x, y)` in a Terrain
Grid produces a 4-bit adjacency mask over its four **orthogonal** neighbours. Each
direction owns one bit:

```text
bit 0 (1) = North  (x,   y-1)
bit 1 (2) = East   (x+1, y  )
bit 2 (4) = South  (x,   y+1)
bit 3 (8) = West   (x-1, y  )
```

A direction bit is set **if and only if** that neighbour exists on the grid **and**
shares the cell's terrain layer. Diagonals are ignored. The mask is deterministic and
always in `[0, 15]`. Cells are visited in row-major order.

Concretely, in a grid where every cell shares one terrain layer:

- an interior cell has all four neighbours present and same-terrain, so its mask is
  `15` (N|E|S|W);
- the corner cell `(0, 0)` has no North and no West neighbour, so at most East|South
  can set — mask `6`;
- a cell whose four neighbours all differ in terrain sets no bit — mask `0`, even
  though the neighbours physically exist.

## Business or Design Value

The adjacency mask is the tile's entire statement about its surroundings; proving it
correct once protects every connectivity decision downstream. It is also the first
rule in the programme rich enough to carry a *relational* invariant — East/West and
North/South symmetry between adjacent cells — which the Verified Model discharges as
lemmas rather than examples.

## Scope

- The pure mask rule as a domain service (`AdjacencyMaskCalculator`) with its value
  objects (`TerrainGrid`, `AdjacencyMask`) in `MapGen.Domain` (bounded context: Tile
  Resolution).
- A command boundary: `ComputeAdjacencyMaskCommand` and its handler in
  `MapGen.Application`, dispatched through Mediator per ADR 0005
  (`IRequest<Result<T>>` / `IRequestHandler<,>` via `ISender`).
- A `mask-cell` subcommand on `MapGen.Cli` as the `net`-profile entry point for the
  BDD lane.
- The Verified Model, already authored and verifying: `specs/tiling/AdjacencyMask.dfy`
  (Level B verified reference).
- Dual-profile BDD for the slice's scenarios; unit, property, architecture, and
  compatibility evidence.

## Out of Scope

- Tile identifier composition (`terrain << 8 | mask`) as a rule of the new code — the
  BDD legacy adapter and the golden fixtures read the packed id as evidence, but
  producing `.maptiles` from new C# is a later slice.
- Cell-to-Tile Expansion itself — proved in Epic 1; this slice computes one mask per
  cell and does not re-derive the 2×2 region.
- Replacing the Tiler stage, its lanes, or its systemd wiring.
- Persistence and queries — no stored mask grid, so no read model.
- Diagonal adjacency, 8-neighbour masks, or any mask wider than 4 bits.

## Legacy Baseline Behaviour

The legacy pipeline's Tiler stage defines current behaviour. The rule lives in
`MapGenerator/Tiler/Processing/CellBitmaskCalculator.cs`: `ComputeMasks(heightmap)`
walks the grid row-major and, per cell, sets North (`|1`) when `y>0` and the cell
above shares terrain, East (`|2`) when `x+1<width` and the cell right shares terrain,
South (`|4`) when `y+1<height` and the cell below shares terrain, West (`|8`) when
`x>0` and the cell left shares terrain. The bit values, the guards, and the row-major
order are the contract this slice adopts verbatim, not accidents to be re-derived.

`TileIdResolver.cs` then packs each cell's mask into the low byte of the tile id
(`terrain << 8 | mask`) and writes the same id into all four tiles of the cell's 2×2
region. So the mask is observable end-to-end in a golden `.maptiles`: the low nibble
of any of a cell's four tiles is that cell's mask.

Golden Job fixtures under `tests/fixtures/golden/` (jobs
`43860dcf-6469-42a7-9843-4e33abeacfac`, `3c96b74c-6f86-4d27-a0ca-c567f385ae8e`,
`0860a05a-a410-4cc2-987d-a48a4cd120c7`) capture the baseline: their `.heightmap`
inputs and `.maptiles` outputs let a compatibility test recompute masks from the
heightmap and confirm they appear in the maptiles low nibbles.

Terrain-byte constraint to preserve, not fix: the legacy `HeightmapReader` validates
terrain as `0..3` (four layers). BDD grids that must run through the legacy binary
therefore use terrain values in `[0, 3]` only. This is a legacy input constraint, not
a rule of the mask itself — the Verified Model and the C# domain accept any terrain
values and compare them for equality; only the `legacy`-profile path is bound to
`0..3`.

Known quirk to preserve, not fix: the legacy stage has no per-cell request surface —
it masks whole maps — so it cannot exhibit rejection of a single out-of-bounds cell.
Rejection is a property of the new command boundary (see the `@net-only` scenario
below), exactly as in Epic 1.

## BDD Scenarios

Feature file: `tests/bdd/features/02-adjacency-mask/adjacency-mask.feature`
(tag `@slice-02-adjacency-mask`):

1. **Mask an interior cell surrounded by the same terrain** — in a 3×3 grid of one
   terrain layer, cell `(1, 1)` has all four neighbours present and same-terrain, so
   its mask is `15`.
2. **Mask the origin corner cell** — in a same-terrain grid, cell `(0, 0)` has no
   North and no West neighbour, so only East|South set: mask `6`.
3. **Mask a cell whose neighbours differ in terrain** — a cell whose four orthogonal
   neighbours each carry a different terrain layer sets no bit: mask `0`.
4. **Symmetry between adjacent cells** — for any two orthogonally adjacent cells, one
   cell sets the bit toward the other exactly when that other sets the bit back
   (East of a cell ⇔ West of the cell to its right; South ⇔ North of the cell below).
   Stated as an observable rule over a small grid, not a mathematical quantifier.
5. **Reject an out-of-bounds cell** — a request for a cell coordinate outside the grid
   fails with a typed failure rather than returning a mask. Tagged `@net-only`: an
   approved, documented profile asymmetry (see Legacy Baseline Behaviour above).

Scenarios 1–4 must be green on both the `legacy` and `net` profiles from the same
Gherkin. The scenarios state the domain rule directly in CONTEXT.md vocabulary; no
Persona acts in them because no operator intent is involved — this is the pipeline's
arithmetic, not a workflow. Persona-bearing scenarios remain in
`tests/bdd/features/00-cross-cutting/`.

Legacy-profile grids use terrain values in `[0, 3]` (the heightmap constraint above);
`net`-profile grids may use any small ints but stay in `[0, 3]` for the shared
scenarios so the two profiles run identical inputs.

## Domain Contract

The framework-free contract that `specs/tiling/AdjacencyMask.dfy` and the
`MapGen.Domain` types both encode. Weakening any line below is a Specification
correction requiring human review.

### Preconditions

- Grid width is greater than zero.
- Grid height is greater than zero.
- Cell `x` is less than the grid width.
- Cell `y` is less than the grid height.

(Coordinates and dimensions are zero-based. Terrain values are compared for equality
only; the domain places no upper bound on them — the `0..3` bound is a legacy input
constraint, not a rule of the mask.)

### Postconditions

- The mask is a single value in `[0, 15]`.
- Bit 0 (North, value 1) is set iff `y > 0` and the cell at `(x, y-1)` shares the
  cell's terrain.
- Bit 1 (East, value 2) is set iff `x+1 < width` and the cell at `(x+1, y)` shares the
  cell's terrain.
- Bit 2 (South, value 4) is set iff `y+1 < height` and the cell at `(x, y+1)` shares
  the cell's terrain.
- Bit 3 (West, value 8) is set iff `x > 0` and the cell at `(x-1, y)` shares the
  cell's terrain.
- The mask is the sum of exactly those four guarded bit contributions; no diagonal
  neighbour and no non-orthogonal cell influences it.

### Invariants

- **Edge cells never set off-map bits.** A cell on the top row never sets North; on
  the left column never sets West; on the bottom row never sets South; on the right
  column never sets East. The corner `(0, 0)` can set at most East|South.
- **Adjacency is symmetric.** For orthogonally adjacent cells, the East bit of a cell
  is set exactly when the West bit of the cell to its right is set, and the South bit
  of a cell is set exactly when the North bit of the cell below it is set. Symmetry is
  a consequence of the same-terrain predicate being symmetric, and it holds for every
  interior pair.
- The bit weights (N=1, E=2, S=4, W=8) and the row-major visitation order are
  contractual — they equal the legacy emission and packing order.

### Failure Modes

- A cell coordinate at or beyond the grid bounds, or non-positive dimensions, is
  rejected at the command boundary with a typed failure naming the violated
  precondition. No exception-as-control-flow, no silent clamping, no default mask.

### Determinism and Idempotency

Deterministic: identical grid and coordinate produce an identical mask — structurally
guaranteed in the Verified Model (Dafny functions are pure) and property-tested in C#.
Idempotency does not apply: the operation is a pure function with no state to re-apply.

## Acceptance Summary

- [ ] The slice's scenarios exist in the feature file; scenarios 1–4 are green on the
      `legacy` profile and all five on the `net` profile.
- [ ] `specs/tiling/AdjacencyMask.dfy` verifies: mask-in-range, edge cells never set
      off-map bits, East/West and North/South symmetry, and bits reflecting the
      neighbour predicate are discharged lemmas.
- [ ] Unit and FsCheck property tests in `tests/MapGen.Domain.Tests` cover the slice's
      test plan (interior, corner, differing-terrain, and generated valid inputs) and
      pass, mirroring the Dafny lemmas.
- [ ] `MapGen.Domain` has no infrastructure dependency and the command handler
      implements `IRequestHandler<,>` (architecture tests pass).
- [ ] Compatibility with the legacy pipeline is demonstrated per `acceptance.md` (the
      BDD legacy nibble probe against the real binary, plus the optional golden
      recompute), with the `@net-only` asymmetry documented.
- [ ] `just quality` is green and the slice tag is appended to both promotion ledgers
      in the closing PR.
