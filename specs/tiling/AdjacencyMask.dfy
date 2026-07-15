// AdjacencyMask.dfy — the verified model for Epic 2 (slice-02-adjacency-mask, issue #10).
//
// Level B verified reference (ADR 0002) for the legacy rule in
// MapGenerator/Tiler/Processing/CellBitmaskCalculator.cs: each cell gets a 4-bit
// adjacency mask over its four orthogonal neighbours.
//
//   bit 0 (1) = North (y-1)   bit 1 (2) = East  (x+1)
//   bit 2 (4) = South (y+1)   bit 3 (8) = West  (x-1)
//
// A direction bit is set iff that neighbour EXISTS on the grid AND shares the cell's
// terrain layer. Diagonals are ignored. Deterministic; mask in [0, 15].
//
// The C# production twin (MapGen.Domain AdjacencyMaskCalculator) must agree with this
// model — checked by FsCheck properties mirroring each lemma and behaviourally by the
// cucumber contract against the legacy Tiler binary and the new implementation.

module AdjacencyMask {

  // A terrain grid: width x height cells, each carrying a terrain value.
  datatype Grid = Grid(width: nat, height: nat, terrain: (nat, nat) -> nat)

  predicate ValidGrid(g: Grid)
  {
    g.width > 0 && g.height > 0
  }

  predicate InBounds(g: Grid, x: nat, y: nat)
  {
    x < g.width && y < g.height
  }

  // The four direction bits, each guarded by "neighbour exists AND same terrain".
  // West/North use nat subtraction guarded by x>0 / y>0 so they never underflow.
  function NorthBit(g: Grid, x: nat, y: nat): nat
    requires InBounds(g, x, y)
  { if y > 0 && g.terrain(x, y - 1) == g.terrain(x, y) then 1 else 0 }

  function EastBit(g: Grid, x: nat, y: nat): nat
    requires InBounds(g, x, y)
  { if x + 1 < g.width && g.terrain(x + 1, y) == g.terrain(x, y) then 2 else 0 }

  function SouthBit(g: Grid, x: nat, y: nat): nat
    requires InBounds(g, x, y)
  { if y + 1 < g.height && g.terrain(x, y + 1) == g.terrain(x, y) then 4 else 0 }

  function WestBit(g: Grid, x: nat, y: nat): nat
    requires InBounds(g, x, y)
  { if x > 0 && g.terrain(x - 1, y) == g.terrain(x, y) then 8 else 0 }

  function Mask(g: Grid, x: nat, y: nat): nat
    requires InBounds(g, x, y)
  {
    NorthBit(g, x, y) + EastBit(g, x, y) + SouthBit(g, x, y) + WestBit(g, x, y)
  }

  // ---- Proved properties ----

  // The mask is always a 4-bit value.
  lemma MaskInRange(g: Grid, x: nat, y: nat)
    requires InBounds(g, x, y)
    ensures 0 <= Mask(g, x, y) <= 15
  {
  }

  // A corner cell (0,0) can only ever set East and South — its North and West
  // neighbours are off the grid, so those bits are never set.
  lemma EdgeCellsNeverSetOffMapBits(g: Grid, x: nat, y: nat)
    requires InBounds(g, x, y)
    ensures y == 0 ==> NorthBit(g, x, y) == 0
    ensures x == 0 ==> WestBit(g, x, y) == 0
    ensures y == g.height - 1 ==> SouthBit(g, x, y) == 0
    ensures x == g.width - 1 ==> EastBit(g, x, y) == 0
  {
  }

  // Symmetry (horizontal): if a cell sees its East neighbour as same-terrain, that
  // neighbour sees this cell as its West neighbour, same-terrain — and vice versa.
  lemma EastWestSymmetry(g: Grid, x: nat, y: nat)
    requires InBounds(g, x, y)
    requires x + 1 < g.width
    ensures (EastBit(g, x, y) == 2) <==> (WestBit(g, x + 1, y) == 8)
  {
  }

  // Symmetry (vertical): South of a cell ⇔ North of the cell below it.
  lemma NorthSouthSymmetry(g: Grid, x: nat, y: nat)
    requires InBounds(g, x, y)
    requires y + 1 < g.height
    ensures (SouthBit(g, x, y) == 4) <==> (NorthBit(g, x, y + 1) == 1)
  {
  }

  // A bit is set exactly when its neighbour predicate holds — no bit is set for a
  // missing neighbour, and a same-terrain neighbour always sets its bit.
  lemma BitsReflectNeighbourPredicate(g: Grid, x: nat, y: nat)
    requires InBounds(g, x, y)
    ensures NorthBit(g, x, y) == 1 <==> (y > 0 && g.terrain(x, y - 1) == g.terrain(x, y))
    ensures EastBit(g, x, y)  == 2 <==> (x + 1 < g.width && g.terrain(x + 1, y) == g.terrain(x, y))
    ensures SouthBit(g, x, y) == 4 <==> (y + 1 < g.height && g.terrain(x, y + 1) == g.terrain(x, y))
    ensures WestBit(g, x, y)  == 8 <==> (x > 0 && g.terrain(x - 1, y) == g.terrain(x, y))
  {
  }
}
