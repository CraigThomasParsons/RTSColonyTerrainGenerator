# Requirements: <NN-slice-name>

<!-- Lifecycle steps 1, 2, and 4: product requirement, BDD scenarios, domain contract. -->

## Problem

What problem exists? Name the player, operator, or system value at stake.

## Desired Behaviour

What should happen? State the rule plainly, in CONTEXT.md vocabulary, with a concrete
example (e.g. "cell (x, y) produces exactly the four tiles of its 2×2 region").

## Business or Design Value

Why does this matter? One or two sentences.

## Scope

What is included in this slice? Keep it thin enough to close in one sprint.

## Out of Scope

What is intentionally excluded? Name the deferrals so nobody "helpfully" adds them.

## Legacy Baseline Behaviour

Which legacy stage(s) define current behaviour, and which Golden Job fixtures capture
it? Note any known legacy quirks that are contract vs. accident.

## BDD Scenarios

List the feature files under `tests/bdd/features/<NN-slice-name>/` and summarize each
scenario in one line. Scenarios describe observable behaviour in domain vocabulary and
reference Personas by name; they do not enumerate mathematical input spaces.

## Domain Contract

The framework-free contract the Dafny model and C# types will encode.

### Preconditions

What must be true before the operation?

### Postconditions

What must be true afterward?

### Invariants

What cannot change? What relationships must always hold?

### Failure Modes

What failures are valid, and how are they represented (typed results, not silence)?

### Determinism and Idempotency

Is the operation deterministic for fixed inputs and seed? Is it idempotent?

## Acceptance Summary

What must be true for the requirement to be accepted? One checklist, phrased so a
reviewer can verify each line.
