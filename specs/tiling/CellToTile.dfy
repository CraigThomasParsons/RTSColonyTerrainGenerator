// CellToTile.dfy — the verified model for Epic 1 (slice-01-cell-to-tile, issue #7).
//
// Level B verified reference (ADR 0002): this module is the formal source of truth for
// the cell-to-tile expansion rule. The C# production implementation (MapGen.Domain
// CellExpander) must agree with it — enforced by unit examples and FsCheck properties
// that mirror the lemmas below, and behaviourally by the cucumber-js contract run
// against both the legacy pipeline and the new implementation.
//
// The rule (mapgen-spec-driven-planning/08, legacy source Tiler/Processing/TileIdResolver.cs):
// a cell (x, y) expands to exactly the four unique in-bounds tile coordinates
//   TL (2x, 2y), TR (2x+1, 2y), BL (2x, 2y+1), BR (2x+1, 2y+1)
// in that contractual order, and tile-map dimensions are exactly double cell-map
// dimensions.
//
// Determinism: ExpandCell is a Dafny function — pure by construction; identical inputs
// yield the identical ordered result. No separate lemma is required or possible to
// state more strongly.

module CellToTile {

  datatype CellCoordinate = CellCoordinate(x: nat, y: nat)
  datatype TileCoordinate = TileCoordinate(x: nat, y: nat)
  datatype CellMapDimensions = CellMapDimensions(width: nat, height: nat)

  predicate ValidDimensions(d: CellMapDimensions)
  {
    d.width > 0 && d.height > 0
  }

  predicate InCellBounds(c: CellCoordinate, d: CellMapDimensions)
  {
    c.x < d.width && c.y < d.height
  }

  // Tile-map dimensions are defined — not merely asserted — as double the cell map.
  function TileMapWidth(d: CellMapDimensions): nat { d.width * 2 }
  function TileMapHeight(d: CellMapDimensions): nat { d.height * 2 }

  predicate InTileBounds(t: TileCoordinate, d: CellMapDimensions)
  {
    t.x < TileMapWidth(d) && t.y < TileMapHeight(d)
  }

  // The rule. Order is contractual: TL, TR, BL, BR (matches the legacy Tiler).
  function ExpandCell(c: CellCoordinate): seq<TileCoordinate>
  {
    [ TileCoordinate(2 * c.x,     2 * c.y),
      TileCoordinate(2 * c.x + 1, 2 * c.y),
      TileCoordinate(2 * c.x,     2 * c.y + 1),
      TileCoordinate(2 * c.x + 1, 2 * c.y + 1) ]
  }

  // ---- Postconditions, each proved as a lemma ----

  lemma ExpandCellProducesExactlyFour(c: CellCoordinate)
    ensures |ExpandCell(c)| == 4
  {
  }

  lemma ExpandCellCoordinatesAreUnique(c: CellCoordinate)
    ensures forall i, j :: 0 <= i < j < |ExpandCell(c)| ==> ExpandCell(c)[i] != ExpandCell(c)[j]
  {
  }

  lemma ExpandCellStaysInTileBounds(c: CellCoordinate, d: CellMapDimensions)
    requires ValidDimensions(d)
    requires InCellBounds(c, d)
    ensures forall t :: t in ExpandCell(c) ==> InTileBounds(t, d)
  {
  }

  // The exact corner coordinates, in the contractual order.
  lemma ExpandCellEmitsTheContractualCorners(c: CellCoordinate)
    ensures ExpandCell(c)[0] == TileCoordinate(2 * c.x,     2 * c.y)
    ensures ExpandCell(c)[1] == TileCoordinate(2 * c.x + 1, 2 * c.y)
    ensures ExpandCell(c)[2] == TileCoordinate(2 * c.x,     2 * c.y + 1)
    ensures ExpandCell(c)[3] == TileCoordinate(2 * c.x + 1, 2 * c.y + 1)
  {
  }

  // Region extrema: the minimum corner is (2x, 2y) and the maximum is (2x+1, 2y+1).
  lemma ExpandCellExtrema(c: CellCoordinate)
    ensures forall t :: t in ExpandCell(c) ==> 2 * c.x <= t.x <= 2 * c.x + 1
    ensures forall t :: t in ExpandCell(c) ==> 2 * c.y <= t.y <= 2 * c.y + 1
  {
  }

  // Distinct cells own disjoint tile regions — no tile belongs to two cells.
  // (Stronger than the charter asks; it is what makes the 2×2 expansion a partition.)
  lemma DistinctCellsHaveDisjointRegions(a: CellCoordinate, b: CellCoordinate)
    requires a != b
    ensures forall t :: t in ExpandCell(a) ==> t !in ExpandCell(b)
  {
  }

  // Every tile of the expanded map belongs to exactly one cell: witness x/2, y/2.
  lemma EveryTileHasAnOwningCell(t: TileCoordinate, d: CellMapDimensions)
    requires ValidDimensions(d)
    requires InTileBounds(t, d)
    ensures var c := CellCoordinate(t.x / 2, t.y / 2);
            InCellBounds(c, d) && t in ExpandCell(c)
  {
  }
}
