@slice-01-cell-to-tile
Feature: Expand a terrain cell into its tile region
  Epic 1's portable contract (charter: mapgen-spec-driven-planning/08). The same
  scenarios run against both targets: the legacy pipeline (the published Tiler binary,
  observed through a marker-terrain probe) and the new C# implementation (MapGen.Cli).
  Spec pack: docs/specs/01-cell-to-tile/.

  Rule: Each cell occupies exactly one 2 by 2 tile region

    Scenario: Expand the origin cell
      Given a cell map that is 10 cells wide and 10 cells high
      When I expand the cell at 0,0
      Then the tile region contains exactly 4 coordinates
      And the tile region contains 0,0
      And the tile region contains 1,0
      And the tile region contains 0,1
      And the tile region contains 1,1

    Scenario: Expand an interior cell
      Given a cell map that is 10 cells wide and 10 cells high
      When I expand the cell at 3,4
      Then the tile region contains exactly 4 coordinates
      And the tile region contains 6,8
      And the tile region contains 7,8
      And the tile region contains 6,9
      And the tile region contains 7,9

    Scenario: Expand the final valid cell
      Given a cell map that is 10 cells wide and 10 cells high
      When I expand the cell at 9,9
      Then every tile coordinate is inside a tile map that is 20 tiles wide and 20 tiles high

    @net-only
    Scenario: Reject an out of bounds cell
      # The legacy stage has no per-cell request surface to reject a coordinate;
      # rejection is a property of the new command boundary (documented asymmetry,
      # docs/specs/01-cell-to-tile/acceptance.md).
      Given a cell map that is 10 cells wide and 10 cells high
      When I try to expand the cell at 10,9
      Then the operation fails because the cell coordinate is outside the cell map
