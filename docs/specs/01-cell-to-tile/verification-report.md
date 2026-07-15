# Verification Report — slice-01-cell-to-tile

Spec: `specs/tiling/CellToTile.dfy` · Dafny 4.11.0 · Verified 2026-07-14 (issue #7)

```
Dafny program verifier finished with 13 verified, 0 errors
```

## What was proved

| Property | Lemma |
|---|---|
| Exactly four coordinates per region | `ExpandCellProducesExactlyFour` |
| All four coordinates unique | `ExpandCellCoordinatesAreUnique` |
| Every coordinate inside the doubled tile map | `ExpandCellStaysInTileBounds` |
| The exact corners, in contractual order TL,TR,BL,BR | `ExpandCellEmitsTheContractualCorners` |
| Region extrema are (2x,2y)…(2x+1,2y+1) | `ExpandCellExtrema` |
| Distinct cells own disjoint regions | `DistinctCellsHaveDisjointRegions` |
| Every in-bounds tile has exactly one owning cell | `EveryTileHasAnOwningCell` |

The last two exceed the charter: together with the others they establish that the
expansion is a **partition** of the tile map — no gaps, no overlaps.

## What was assumed

- No `assume` statements, no `{:axiom}`, no `ghost`-hidden behaviour, no `decreases`
  clauses needed (no loops or recursion).
- Tile-map doubling is a *definition* (`TileMapWidth/Height`), not an assumption — the
  compatibility suite checks the legacy pipeline's real artifacts obey it
  (`GoldenTilerDimensionsTest`).

## What was NOT proved (and how it is covered instead)

- **Determinism** is structural (Dafny functions are pure) — it cannot be stated as a
  stronger lemma. The production twin is checked by the FsCheck property
  `Expansion_is_deterministic`, which caught a real C# value-equality defect in
  `TileRegion` during this slice.
- **The C# implementation itself** is not verified — it is *checked against* this model
  by FsCheck properties mirroring each lemma (`CellExpanderPropertyTests`, one property
  per lemma, named in comments) and behaviourally by the cucumber contract green on
  both profiles.
- **The legacy Tiler's per-cell behaviour** is demonstrated, not proved: the BDD legacy
  adapter probes the published binary with a marker terrain value and observes the four
  tiles that carry it. Coverage is per-scenario, not universal.

## Relationship between model, production code, and tests

```
CellToTile.dfy (proved)  ←mirrors→  CellExpanderPropertyTests (checked, 500 cases each)
        ↓ defines                         ↓ exercises
   the contract          →implements→  CellExpander (C#)  →driven by→  MapGen.Cli
                                          ↑ compared with
                          legacy Tiler binary (BDD marker probe + golden artifacts)
```
