@slice-02-adjacency-mask
Feature: Compute a cell's adjacency mask
  Epic 2's portable contract (issue #10). A cell's 4-bit mask records which of its four
  orthogonal neighbours share its terrain: North=1, East=2, South=4, West=8. The same
  scenarios run against the legacy pipeline (the published Tiler binary, read through the
  tile-id low nibble) and the new C# implementation (MapGen.Cli mask-cell).
  Spec pack: docs/specs/02-adjacency-mask/. Terrain values stay in 0..3 (legacy range).

  Rule: A direction bit is set iff that neighbour exists and shares the cell's terrain

    Scenario: A cell surrounded by the same terrain sets all four bits
      Given a 3 by 3 terrain grid with rows "1,1,1 / 1,1,1 / 1,1,1"
      When I compute the adjacency mask at 1,1
      Then the adjacency mask is 15

    Scenario: A corner cell can only see East and South
      Given a 3 by 3 terrain grid with rows "1,1,1 / 1,1,1 / 1,1,1"
      When I compute the adjacency mask at 0,0
      Then the adjacency mask is 6
      And the mask has East and South but not North or West

    Scenario: A cell whose neighbours differ sets no bits
      Given a 3 by 3 terrain grid with rows "1,2,1 / 2,3,2 / 1,2,1"
      When I compute the adjacency mask at 1,1
      Then the adjacency mask is 0

    Scenario: Only matching neighbours set their bit
      Given a 3 by 3 terrain grid with rows "0,1,0 / 2,1,2 / 0,1,0"
      When I compute the adjacency mask at 1,1
      Then the adjacency mask is 5
      And the mask has North and South but not East or West

    @net-only
    Scenario: Reject an out of bounds cell
      # As in slice-01, the legacy stage has no per-cell request surface to reject.
      Given a 3 by 3 terrain grid with rows "1,1,1 / 1,1,1 / 1,1,1"
      When I try to compute the adjacency mask at 3,1
      Then the operation fails because the cell coordinate is outside the cell map
