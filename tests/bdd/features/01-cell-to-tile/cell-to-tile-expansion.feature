@slice-01-cell-to-tile @wip
Feature: Expand terrain cells into tiles
  Epic 1's portable contract (mapgen-spec-driven-planning/08-first-epic-verified-cell-to-tile.md).
  Tagged @wip until its steps exist: the Epic 1 slice proves these scenarios against the
  legacy Tiler, verifies the rule in the Dafny verified model, then implements it in
  MapGen.Domain — the same Gherkin must go green on both profiles before promotion.

  Rule: One cell produces one 2 by 2 tile region

    Scenario: Expand the origin cell
      Given a terrain map with a width of 10 cells and a height of 10 cells
      When cell 0,0 is expanded
      Then the generated tile coordinates are:
        | x | y |
        | 0 | 0 |
        | 1 | 0 |
        | 0 | 1 |
        | 1 | 1 |

    Scenario: Expand a cell near the far boundary
      Given a terrain map with a width of 10 cells and a height of 10 cells
      When cell 9,9 is expanded
      Then all generated tile coordinates are inside a 20 by 20 tile map
