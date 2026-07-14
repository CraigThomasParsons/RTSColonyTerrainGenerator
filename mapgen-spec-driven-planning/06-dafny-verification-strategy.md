# Dafny Verification Strategy

## Purpose

Dafny will provide machine-checked evidence for selected domain rules. It is a tool for eliminating classes of logic errors, not a replacement for product review, testing, or operational monitoring.

## Verification Levels

### Level 1 — Structural contracts

Verify basic relationships:

- dimensions;
- bounds;
- non-empty requirements;
- exact output counts;
- uniqueness;
- valid ranges.

Use this level first.

### Level 2 — State and transition contracts

Verify:

- allowed transitions;
- terminal-state behaviour;
- retry semantics;
- idempotency models;
- dependency ordering.

### Level 3 — Algorithm validity

Verify:

- produced paths are valid;
- all placements satisfy constraints;
- algorithms terminate;
- transformations preserve required information.

### Level 4 — Stronger properties

Potential later work:

- path optimality;
- equivalence of alternative algorithms;
- stronger determinism guarantees;
- conservation across complex operations.

Do not begin with Level 4.

## Initial Specification Modules

```text
specifications/
├── Common/
│   ├── Coordinates.dfy
│   ├── Dimensions.dfy
│   └── Results.dfy
├── TileResolution/
│   ├── CellExpansion.dfy
│   ├── AdjacencyMask.dfy
│   └── TileMapContract.dfy
├── PipelineLifecycle/
│   ├── StageState.dfy
│   └── JobTransitions.dfy
├── Vegetation/
│   ├── PlacementContract.dfy
│   └── SuitabilityContract.dfy
└── Traversal/
    ├── PathContract.dfy
    └── TraversalActions.dfy
```

## Example: Cell Expansion

```dafny
datatype Coordinate = Coordinate(x: nat, y: nat)

function ExpandCell(cell: Coordinate): seq<Coordinate>
{
  [
    Coordinate(cell.x * 2,     cell.y * 2),
    Coordinate(cell.x * 2 + 1, cell.y * 2),
    Coordinate(cell.x * 2,     cell.y * 2 + 1),
    Coordinate(cell.x * 2 + 1, cell.y * 2 + 1)
  ]
}

predicate InBounds(point: Coordinate, width: nat, height: nat)
{
  point.x < width && point.y < height
}

lemma ExpandedCellHasFourTiles(cell: Coordinate)
  ensures |ExpandCell(cell)| == 4
{
}

lemma ExpandedCellIsInBounds(
  cell: Coordinate,
  cellWidth: nat,
  cellHeight: nat)
  requires cellWidth > 0
  requires cellHeight > 0
  requires InBounds(cell, cellWidth, cellHeight)
  ensures forall tile ::
    tile in ExpandCell(cell) ==>
      InBounds(tile, cellWidth * 2, cellHeight * 2)
{
}
```

This specification should be refined as actual Dafny syntax and project conventions are established.

## Specification Review Checklist

A human reviewer should ask:

- Does the contract express the intended behaviour?
- Are the preconditions too strong?
- Are the postconditions meaningful?
- Could a broken implementation satisfy the specification?
- Does the model accidentally omit an important failure?
- Are units and coordinate systems explicit?
- Is determinism defined at the correct level?
- Are ordering requirements intentional?
- Is the specification independent of implementation details?

## Prohibited Agent Shortcuts

Agents must not:

- replace meaningful predicates with `true`;
- weaken `requires` or `ensures` clauses merely to pass verification;
- add `assume` statements to bypass proof obligations;
- introduce unchecked axioms;
- remove loop invariants without justification;
- hide failures by reducing the verified scope;
- alter the specification and implementation in the same change without clearly identifying the contract change;
- treat successful verification as proof that the product requirement is correct.

Any approved assumption must be documented with:

- why it is necessary;
- who owns the assumption;
- how it is tested or monitored;
- how it could later be removed.

## Relationship to C#

Three integration patterns are allowed.

### Pattern A — Independent model

Dafny defines expected behaviour. C# is tested against examples and generated cases from the same model.

Use when:

- integration with existing code matters;
- the C# implementation must be idiomatic;
- direct compilation from Dafny is unnecessary.

### Pattern B — Verified reference implementation

Dafny produces canonical outputs for fixtures. C# compatibility tests compare logical outputs.

Use when:

- replacing a legacy stage;
- exact behavioural parity is important;
- the algorithm is manageable in Dafny.

### Pattern C — Compiled Dafny component

The verified Dafny implementation is compiled and invoked directly.

Use when:

- the component is small and stable;
- generated-code boundaries are acceptable;
- performance and deployment are understood;
- debugging remains practical.

Pattern A is the default starting point.

## What Not to Verify First

Do not start with:

- systemd unit behaviour;
- command-line parsing;
- Serilog configuration;
- dependency injection;
- JSON formatting;
- HTML debug pages;
- framework middleware;
- process launching;
- exact visual appearance.

These remain important, but tests and operational checks are more appropriate.

## Verification Report

Each verified component should have a short report:

```markdown
# Verification Report: <Component>

## Requirement
What behaviour is being protected?

## Properties Proved
List the exact guarantees.

## Preconditions
List assumptions callers must satisfy.

## Not Proved
State important exclusions.

## Production Relationship
Explain whether Dafny is a model, reference, or compiled implementation.

## Test Relationship
Explain how C# and integration tests connect to the specification.
```
