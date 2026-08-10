# AGENTS.md

## Project Mission

Develop the Map Generation Pipeline through a specification-driven workflow:

```text
Product requirement
        ↓
BDD scenarios
        ↓
Bounded context and domain model
        ↓
Domain contract
        ↓
Dafny model, proof, or verified reference implementation
        ↓
CQRS command/query design
        ↓
C# production implementation
        ↓
Unit, integration, compatibility, and acceptance tests
```

## Mandatory Work Order

For any change that modifies domain behaviour:

1. Locate or create the product requirement.
2. Locate or create BDD scenarios.
3. Identify the bounded context that owns the behaviour.
4. Write or update the domain contract.
5. Write or update the Dafny specification when the rule is verification-worthy.
6. Define commands, queries, results, and events.
7. Implement domain behaviour in C#.
8. Add unit, property, integration, compatibility, and acceptance tests as appropriate.
9. Run all available quality gates.
10. Report anything that remains unverified.

## Human-Controlled Artifacts

The following require explicit human review when their meaning changes:

- product acceptance criteria;
- BDD expected outcomes;
- domain invariants;
- Dafny `requires` clauses;
- Dafny `ensures` clauses;
- domain predicates;
- artifact schemas;
- stage-transition rules;
- compatibility normalization rules.

An agent may propose changes to these artifacts, but it must identify the proposal as a specification change. It must not silently change them to make code or proofs pass.

## Prohibited Shortcuts

Do not:

- weaken a contract merely to satisfy the verifier;
- replace a meaningful predicate with `true`;
- add `assume`, unchecked axioms, or equivalent bypasses without explicit approval;
- delete a failing test or scenario instead of correcting the behaviour;
- rewrite golden fixtures without documenting the behavioural change;
- move domain logic into command handlers, controllers, CLI commands, workers, or infrastructure adapters;
- report a stage as successful before validating and atomically committing its output artifact;
- merge directly into `develop` or `main`;
- modify unrelated code while completing a focused task.

## Domain Rules

- Use the ubiquitous language from the owning bounded context.
- Prefer explicit value objects for coordinates, dimensions, identifiers, hashes, seeds, versions, and state.
- Keep deterministic domain operations independent from clocks, filesystems, global random generators, and environment variables.
- Represent expected failure explicitly.
- Enforce invariants inside the owning domain type or service.
- Do not share large mutable models across bounded contexts.

## CQRS Rules

- Commands request a state change or effect.
- Queries retrieve information and must not mutate state.
- Command and query handlers coordinate work; they do not own core domain algorithms.
- Validation at an application boundary does not replace domain enforcement.
- Integration events use versioned contracts.
- Mediator is an implementation mechanism, not the owner of message semantics.

## Dafny Rules

- All maintained `.dfy` files must verify.
- State exactly what is proved and what is not proved.
- Use meaningful invariants and termination measures.
- Keep specifications independent of framework and persistence details.
- Default to using Dafny as a model or verified reference implementation.
- Directly compiled Dafny components require an explicit architecture decision.
- Report verification timeouts, instability, or solver-sensitive proofs.

## Testing Rules

Use:

- unit tests for examples and local domain behaviour;
- property tests for mathematical and invariant-heavy rules;
- architecture tests for dependency boundaries;
- integration tests for files, processes, databases, and adapters;
- compatibility tests when replacing a legacy implementation;
- acceptance tests for BDD scenarios.

Every corrected defect must receive a regression test.

## Artifact Safety

- Treat committed artifacts as immutable.
- Use versioned schemas.
- Include input lineage and hashes.
- Write to temporary locations first.
- Validate before atomic promotion.
- Never present a temporary or partially written artifact as complete.
- Preserve backwards-compatible readers during staged migrations.

## Expected Commands

Use the repository commands when they exist:

```text
just format
just build
just verify
just test-unit
just test-integration
just test-compatibility
just test-acceptance
just quality
```

When a command cannot run, report the exact command and reason.

## Required Completion Report

```markdown
## Change Classification

## Requirement and BDD

## Bounded Context and Contract

## Dafny Verification

## CQRS and C# Implementation

## Tests and Compatibility

## Remaining Risks or Unverified Work
```
