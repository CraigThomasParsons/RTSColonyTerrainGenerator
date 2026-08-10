# ADR-001: Adopt a Specification-Driven Architecture for Map Generation

- **Status:** Proposed
- **Decision Owners:** Craig Parsons and project maintainers
- **Date:** 2026-07-13

## Context

The Map Generation Pipeline contains multiple stages implemented in several languages and connected through filesystem-based job and artifact handoffs.

The pipeline is increasingly being developed with coding agents. Natural-language prompts and tests alone do not provide enough protection for correctness-critical rules such as:

- coordinate transformations;
- dimensional consistency;
- deterministic generation;
- valid state transitions;
- vegetation constraints;
- artifact lineage;
- path validity;
- retry and idempotency behaviour.

The project also intends to use DDD, Clean Architecture, CQRS, BDD, and C# for production development.

## Decision

Adopt the following development lifecycle for significant domain behaviour:

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
Integration and acceptance tests
```

Use Dafny selectively for domain rules that benefit from universal or mathematical guarantees.

Use C# as the target production language for newly migrated application and domain components unless a stage has a strong reason to remain in its current language.

Use an incremental strangler migration rather than a full rewrite.

## Rationale

This decision:

- gives agents machine-checkable constraints;
- makes domain rules visible and reviewable;
- complements BDD examples with universal properties;
- supports gradual migration;
- separates domain logic from orchestration and infrastructure;
- creates stronger CI quality gates;
- improves confidence in deterministic and boundary-sensitive algorithms.

## Consequences

### Positive

- domain behaviour becomes explicit;
- important properties can be verified for all valid inputs;
- agents receive clearer constraints;
- regressions are detected earlier;
- pipeline stages become more replaceable;
- state transitions and artifact contracts become auditable;
- C# implementation follows explicit use cases through CQRS.

### Negative

- contributors must learn Dafny concepts;
- proof maintenance adds work;
- specifications can be wrong or incomplete;
- CI becomes more complex;
- dual-run compatibility testing may be temporarily expensive;
- the repository will contain multiple representations of behaviour.

### Risks

- agents may weaken specifications;
- the team may over-verify low-value code;
- formal models may diverge from production code;
- a big-bang rewrite may be attempted despite the migration strategy;
- generated Dafny code may be adopted without sufficient operational evaluation.

## Mitigations

- require human review for contract changes;
- prohibit unapproved assumptions and axioms;
- begin with structural invariants;
- connect Dafny models to C# property and compatibility tests;
- maintain explicit verification reports;
- migrate one vertical slice at a time;
- preserve legacy adapters until parity is demonstrated.

## First Implementation

The first vertical slice will be Verified Cell-to-Tile Expansion in the Tile Resolution bounded context.

This slice will establish:

- requirement templates;
- Gherkin acceptance tests;
- Dafny verification;
- C# domain and application projects;
- CQRS conventions;
- property tests;
- compatibility tests;
- CI gates.

## Alternatives Considered

### Tests only

Rejected as the sole strategy because example-based tests cannot cover all valid coordinate, dimension, transition, and path combinations.

### Dafny for the entire system

Rejected because infrastructure and framework code do not justify the verification cost.

### Full rewrite in C#

Rejected because it creates unnecessary delivery and compatibility risk.

### Keep all current languages permanently

Not rejected categorically. Stable stages may remain in their existing languages, but they must gain explicit contracts, adapters, observability, and compatibility tests.

## Review Trigger

Revisit this ADR when:

- the first three verified vertical slices are complete;
- Dafny maintenance cost materially exceeds benefit;
- compiled Dafny integration is being considered;
- the filesystem transport is replaced;
- stage boundaries or bounded contexts materially change.
