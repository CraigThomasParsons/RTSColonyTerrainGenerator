# Verification Report — slice-02-adjacency-mask

Spec: `specs/tiling/AdjacencyMask.dfy` · Dafny 4.11.0 · Verified 2026-07-15 (issue #10)

```
Dafny program verifier finished with 15 verified, 0 errors
```

## What was proved

| Property | Lemma |
|---|---|
| Mask is always a 4-bit value (0..15) | `MaskInRange` |
| Each bit is set exactly when its neighbour predicate holds | `BitsReflectNeighbourPredicate` |
| Edge cells never set a bit for an off-map neighbour | `EdgeCellsNeverSetOffMapBits` |
| East/West symmetry: my East bit ⇔ my right neighbour's West bit | `EastWestSymmetry` |
| North/South symmetry: my South bit ⇔ the cell below's North bit | `NorthSouthSymmetry` |

The two symmetry lemmas exceed the charter: they establish that adjacency is a consistent
relation across the grid — two neighbours always agree about the edge between them.

## What was assumed

- No `assume`, no `{:axiom}`, no ghost-hidden behaviour, no `decreases` (no recursion).
- The grid is modelled with a total terrain function `(nat, nat) -> nat`; bounds are
  guarded by `InBounds` on every lemma, and West/North guard their `nat` subtraction with
  `x > 0` / `y > 0` so no underflow is possible.

## What was NOT proved (and how it is covered instead)

- **Determinism** is structural (pure functions). Checked in production by the FsCheck
  property `Computation_is_deterministic`.
- **The C# implementation** is checked against this model, not verified: six FsCheck
  properties in `AdjacencyMaskPropertyTests` mirror the five lemmas plus determinism, one
  per lemma, named in comments.
- **The legacy Tiler's behaviour** is demonstrated per-scenario, not proved: the BDD
  legacy adapter reads the mask out of the published binary's tile-id low nibble.
- **Terrain range.** The domain accepts any `int` terrain values; the legacy heightmap
  format restricts terrain to `0..3`. This is an input bound of the legacy format, not a
  rule of the mask, so BDD grids stay in `0..3` while the domain and its properties range
  wider. Recorded in the spec pack.

## Relationship between model, production code, and tests

```
AdjacencyMask.dfy (proved)  ←mirrors→  AdjacencyMaskPropertyTests (checked, 500 cases each)
        ↓ defines                          ↓ exercises
   the contract          →implements→  AdjacencyMaskCalculator (C#)  →via Mediator→ MapGen.Cli mask-cell
                                          ↑ compared with
                          legacy Tiler binary (BDD low-nibble probe)
```
