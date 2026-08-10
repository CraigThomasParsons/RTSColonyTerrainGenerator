# Design: <NN-slice-name>

<!-- Lifecycle steps 3, 5, and 6: bounded context and domain model, Dafny strategy, CQRS design. -->

## Bounded Context

Which context owns this rule (see CONTEXT.md for the list), and why it — not an
adjacent stage — owns it.

## Domain Model

The aggregate or domain service responsible, the value objects involved, upstream
inputs, and downstream outputs. New ubiquitous-language terms go to CONTEXT.md in the
same change.

```text
Bounded Context: <name>
Domain Service / Aggregate: <name>
Inputs: <value objects>
Output: <value object>
Invariant: <one-line statement>
```

## Dafny Strategy

Which verification level (A: executable model, B: verified reference, C: compiled)
and which integration pattern (independent model / reference for fixtures / compiled
component), which `.dfy` files under `specs/` carry it, and why this rule earns
formal treatment. Level A or B is the default starting point.

## CQRS Design

The commands, queries, result types, and events this slice adds or changes. Handlers
orchestrate; they do not reproduce domain arithmetic.

```csharp
public sealed record <Name>Command(...);
public sealed record <Name>Result(...);
```

## Legacy Adapter Boundary

Which interface fronts the legacy stage, what the process adapter does, and what the
future verified C# implementation replaces. The application layer must not know which
implementation is active.

## Architectural Rules and Enforcement

Every rule this design imposes, each with its named enforcement path (architecture
test, Dafny obligation, property test, compatibility test, review checklist). A rule
with no enforcement path does not belong here.

## Trade-offs, Non-Goals, and Risks

What was considered and rejected; what this design deliberately does not solve; what
could go wrong during migration.
