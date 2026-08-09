# Specification-to-Code Workflow

## Required Feature Lifecycle

Every significant domain change should move through the following lifecycle.

## Step 1 — Product Requirement

The requirement explains the player, operator, or system value.

Template:

```markdown
# Requirement: <Name>

## Problem
What problem exists?

## Desired Behaviour
What should happen?

## Business or Design Value
Why does this matter?

## Scope
What is included?

## Out of Scope
What is intentionally excluded?

## Acceptance Summary
What must be true for the requirement to be accepted?
```

Example:

```markdown
# Requirement: Deterministic Cell-to-Tile Expansion

For a terrain cell at coordinate `(x, y)`, the tiler must create exactly four
tile coordinates in the corresponding 2×2 tile region.

The same input cell must always produce the same coordinates.
No generated coordinate may fall outside the expanded tile map.
```

## Step 2 — BDD Scenarios

BDD captures examples understandable to non-specialists.

```gherkin
Feature: Expand terrain cells into tiles

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
```

BDD should emphasize observable behaviour. It should not attempt to enumerate every mathematical input.

## Step 3 — Bounded Context and Domain Model

Before writing code, identify:

- the bounded context that owns the rule;
- the aggregate or domain service responsible;
- the value objects involved;
- the ubiquitous language;
- upstream inputs;
- downstream outputs;
- invariants;
- failure modes.

Example:

```text
Bounded Context: Tile Resolution
Domain Service: CellExpander
Inputs: TerrainCellCoordinate, CellMapDimensions
Output: TileRegion
Invariant: TileRegion contains exactly four unique in-bounds coordinates
```

## Step 4 — Domain Contract

Write the contract independently of framework and storage concerns.

Contract questions:

- What must be true before the operation?
- What must be true afterward?
- What cannot change?
- What failures are valid?
- Is the operation deterministic?
- Is the operation idempotent?
- What relationships must always hold?

Example:

```text
Preconditions:
- cell width and height are greater than zero;
- x is less than cell width;
- y is less than cell height.

Postconditions:
- exactly four tile coordinates are returned;
- all four coordinates are unique;
- every coordinate is inside width*2 by height*2;
- the minimum tile coordinate is x*2,y*2;
- the maximum tile coordinate is x*2+1,y*2+1.
```

## Step 5 — Dafny Model or Verified Implementation

Choose one of three levels.

### Level A — Executable mathematical model

Use Dafny to define the expected relationship. The production implementation may remain in C# and be checked through tests generated from or compared against the model.

### Level B — Verified reference implementation

Create a small verified algorithm that acts as the source of truth. The C# implementation must agree with it through compatibility tests.

### Level C — Compiled verified implementation

Compile the Dafny implementation into a target language and use it directly where operationally appropriate.

Most pipeline features should begin at Level A or Level B.

## Step 6 — CQRS Design

Define the use case explicitly.

Example command:

```csharp
public sealed record ResolveTileRegionCommand(
    Guid JobId,
    CellCoordinate Cell,
    CellMapDimensions Dimensions);
```

Example result:

```csharp
public sealed record ResolveTileRegionResult(
    TileRegion Region);
```

The command handler should:

1. validate application-level input;
2. load required state;
3. call the domain operation;
4. persist or publish the result;
5. record observable stage state.

The handler should not reproduce domain arithmetic.

## Step 7 — C# Domain Implementation

Implement:

- immutable value objects where practical;
- explicit result or failure types;
- domain methods that enforce invariants;
- no primitive obsession for important concepts;
- no framework dependencies in the domain;
- deterministic functions for deterministic rules.

## Step 8 — Tests

### Unit tests

Protect:

- domain examples;
- boundary cases;
- failure cases;
- value-object validation.

### Property-based tests

Protect mathematical relationships over many generated inputs.

Recommended use:

- coordinate transforms;
- round trips;
- determinism;
- uniqueness;
- bounds;
- conservation.

### Compatibility tests

Compare legacy and replacement stage outputs at the logical level.

Ignore non-deterministic metadata such as timestamps when it is not part of the contract.

### Integration tests

Protect:

- readers and writers;
- process adapters;
- database persistence;
- filesystem transitions;
- message handling;
- atomic artifact commits.

### Acceptance tests

Execute BDD scenarios against the assembled application.

## Step 9 — Pull Request Evidence

Each domain-changing pull request should include:

```markdown
## Requirement
Link or path.

## BDD
Scenarios added or changed.

## Contract
Invariants added or changed.

## Dafny
Verification result and files affected.

## CQRS
Commands, queries, handlers, or events affected.

## Compatibility
Old-versus-new comparison status.

## Risks
Known limitations and migration concerns.
```

## Definition of Done

A feature is complete when:

- the requirement is approved;
- BDD scenarios are executable;
- the owning bounded context is identified;
- contracts are explicit;
- relevant Dafny specifications verify;
- command/query boundaries are clear;
- C# domain code enforces the same rules;
- unit and integration tests pass;
- acceptance tests pass;
- compatibility is demonstrated if replacing legacy code;
- no specification was weakened without human approval.
