# Epic 1 — Verified Cell-to-Tile Expansion

## Epic Goal

Introduce the full specification-driven development workflow by replacing or wrapping one narrow part of the current Tiler:

> Convert one terrain-cell coordinate into the four tile coordinates belonging to its 2×2 tile region.

This epic is deliberately small. Its purpose is to establish the process, project structure, CI gates, and review habits before larger migration work begins.

## Product Requirement

A terrain map is represented as cells. The tile map expands each cell into a 2×2 tile region.

For every valid cell coordinate:

- exactly four tile coordinates are produced;
- all coordinates are unique;
- all coordinates are inside the expanded tile map;
- the mapping is deterministic;
- the mapping uses the agreed coordinate order.

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Cell | One logical terrain position in the source map |
| Tile | One resolved position in the expanded map |
| Cell Coordinate | Zero-based `(x, y)` coordinate in cell space |
| Tile Coordinate | Zero-based `(x, y)` coordinate in tile space |
| Tile Region | The four tiles belonging to one cell |
| Cell Map Dimensions | Width and height measured in cells |
| Tile Map Dimensions | Width and height measured in tiles |

## BDD Feature

```gherkin
Feature: Expand a terrain cell into its tile region

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
    Then the tile region contains 6,8
    And the tile region contains 7,8
    And the tile region contains 6,9
    And the tile region contains 7,9

  Scenario: Expand the final valid cell
    Given a cell map that is 10 cells wide and 10 cells high
    When I expand the cell at 9,9
    Then every tile coordinate is inside a tile map that is 20 tiles wide and 20 tiles high

  Scenario: Reject an out of bounds cell
    Given a cell map that is 10 cells wide and 10 cells high
    When I try to expand the cell at 10,9
    Then the operation fails because the cell coordinate is outside the cell map
```

## Domain Ownership

Bounded Context:

```text
Tile Resolution
```

Domain service:

```text
CellExpander
```

Value objects:

```text
CellCoordinate
CellMapDimensions
TileCoordinate
TileMapDimensions
TileRegion
```

## Domain Contract

### Preconditions

- map width is greater than zero;
- map height is greater than zero;
- cell `x` is less than map width;
- cell `y` is less than map height.

### Postconditions

- the result contains exactly four coordinates;
- all result coordinates are unique;
- every result coordinate is inside `(width × 2, height × 2)`;
- the coordinates are:

```text
(x × 2,     y × 2)
(x × 2 + 1, y × 2)
(x × 2,     y × 2 + 1)
(x × 2 + 1, y × 2 + 1)
```

### Determinism

Identical inputs produce an identical ordered result.

## Dafny Work Items

- define coordinate datatype;
- define in-bounds predicate;
- define `ExpandCell`;
- prove result length is four;
- prove all coordinates are in bounds;
- prove the four coordinates are unique;
- prove tile-map dimensions are exactly double cell-map dimensions;
- document assumptions and unproved properties.

## CQRS Work Items

### Command

```csharp
public sealed record ResolveTileRegionCommand(
    CellCoordinate Cell,
    CellMapDimensions Dimensions);
```

### Handler Responsibility

- validate the request;
- call `CellExpander`;
- return the resulting `TileRegion`.

For this first epic, persistence is unnecessary.

### Query

A separate query is not required for the pure operation. When the result is persisted as part of a tile-map artifact, a query such as `GetResolvedTileRegion` may be introduced.

## C# Domain Sketch

```csharp
public readonly record struct CellCoordinate(int X, int Y);
public readonly record struct TileCoordinate(int X, int Y);

public sealed record CellMapDimensions
{
    public int Width { get; }
    public int Height { get; }

    public CellMapDimensions(int width, int height)
    {
        if (width <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(width));
        }

        if (height <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(height));
        }

        Width = width;
        Height = height;
    }
}
```

The final implementation should use the project's preferred typed-result and exception policy.

## Test Plan

### Unit Tests

- origin cell;
- interior cell;
- final valid cell;
- negative coordinate;
- coordinate equal to width;
- coordinate equal to height;
- zero dimensions;
- negative dimensions.

### Property Tests

For generated valid dimensions and cells:

- result count is four;
- all coordinates are distinct;
- all coordinates are in bounds;
- minimum `x` equals `cell.x * 2`;
- maximum `x` equals `cell.x * 2 + 1`;
- minimum `y` equals `cell.y * 2`;
- maximum `y` equals `cell.y * 2 + 1`;
- a second call returns an identical result.

### Compatibility Tests

Select representative cells from current Tiler fixtures and compare the logical coordinates.

If the existing ordering differs, decide whether order is contractual or whether comparison should treat the region as a set.

## Tasks

### Planning

- [ ] Approve ubiquitous language.
- [ ] Approve coordinate ordering.
- [ ] Confirm zero-based coordinates.
- [ ] Identify current Tiler function responsible.

### Repository

- [ ] Add specification directories.
- [ ] Add C# Domain, Application, and test projects.
- [ ] Add Dafny verification command.
- [ ] Add BDD test framework.
- [ ] Add property-testing library.

### Specification

- [ ] Write requirement.
- [ ] Add Gherkin feature.
- [ ] Write domain-contract document.
- [ ] Implement Dafny model.
- [ ] Verify required lemmas.
- [ ] Add verification report.

### Implementation

- [ ] Implement value objects.
- [ ] Implement `CellExpander`.
- [ ] Add command and handler.
- [ ] Add unit tests.
- [ ] Add property tests.
- [ ] Add compatibility fixture adapter.

### CI

- [ ] Build C# projects.
- [ ] Run Dafny verification.
- [ ] Run domain tests.
- [ ] Run compatibility tests.
- [ ] Publish failure diagnostics.

## Exit Criteria

The epic is complete when:

- all BDD scenarios pass;
- all Dafny properties verify;
- property tests pass;
- the C# implementation has no infrastructure dependency;
- compatibility with the current Tiler is demonstrated or intentional differences are approved;
- CI enforces the new verification and testing steps;
- the workflow is documented well enough for an agent to repeat it.
