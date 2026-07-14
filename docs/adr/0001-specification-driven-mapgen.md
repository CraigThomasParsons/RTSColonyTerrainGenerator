# ADR 0001: Adopt a Specification-Driven Architecture for Map Generation

- **Status:** Accepted (2026-07-13)
- **Decision Owners:** Craig Parsons and project maintainers

Adapted into ADR form from `mapgen-spec-driven-planning/10-adr-001-specification-driven-mapgen.md`;
the planning pack in `mapgen-spec-driven-planning/` is the full rationale.

## Context

The Map Generation Pipeline contains multiple stages implemented in several languages
(Rust, C#, PHP, Kotlin, Python) and connected through filesystem-based job and
artifact handoffs (`docs/Stage_Contract.md`).

The pipeline is increasingly being developed with coding agents. Natural-language
prompts and tests alone do not provide enough protection for correctness-critical
rules such as:

- coordinate transformations;
- dimensional consistency;
- deterministic generation;
- valid state transitions;
- vegetation constraints;
- artifact lineage;
- path validity;
- retry and idempotency behaviour.

The project also intends to use DDD, Clean Architecture, CQRS, BDD, and C# for
production development, with the legacy stages remaining operational throughout the
migration. The final acceptance target is emitting AgileMedievalPeasantBoard's 64×64
map-document JSON payload.

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

Specifically:

- Use Dafny selectively, for domain rules that benefit from universal or mathematical
  guarantees (see ADR 0002); do not force it into infrastructure code.
- Use C# as the target production language for newly migrated application and domain
  components unless a stage has a strong reason to remain in its current language.
- Use an incremental strangler migration — one vertical Slice at a time, each legacy
  stage behind an interface — rather than a full rewrite.
- Record each slice's specification as a Spec Pack under `docs/specs/<NN-slice-name>/`
  (see `docs/specs/spec-driven-development/README.md`), and each slice's completion as
  an explicit Promotion in the ledgers (`specs/dafny-ready.tags`,
  `tests/bdd/net-ready.tags`).

The first vertical slice is Verified Cell-to-Tile Expansion in the Tile Resolution
bounded context. It establishes the requirement templates, Gherkin acceptance tests,
Dafny verification, C# domain and application projects, CQRS conventions, property
tests, compatibility tests, and CI gates.

## Considered Alternatives

- **Tests only.** Rejected as the sole strategy: example-based tests cannot cover all
  valid coordinate, dimension, transition, and path combinations.
- **Dafny for the entire system.** Rejected: infrastructure and framework code do not
  justify the verification cost.
- **Full rewrite in C#.** Rejected: unnecessary delivery and compatibility risk.
- **Keep all current languages permanently.** Not rejected categorically: stable
  stages may remain in their languages, but they must gain explicit contracts,
  adapters, observability, and compatibility tests.

## Consequences

### Positive

- domain behaviour becomes explicit and reviewable;
- important properties can be verified for all valid inputs;
- agents receive machine-checkable constraints instead of broad prose;
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

### Risks and Mitigations

- *Agents may weaken specifications* → contract changes require human review;
  unapproved assumptions and axioms are prohibited (`AGENTS.md`).
- *Over-verifying low-value code* → begin with structural invariants; Dafny is
  selective by rule.
- *Formal models diverging from production code* → Dafny models are connected to C#
  property and compatibility tests; explicit verification reports are maintained.
- *Big-bang rewrite pressure* → migrate one vertical slice at a time; preserve legacy
  adapters until parity is demonstrated.
- *Compiled Dafny adopted without evaluation* → Pattern C requires its own decision
  (see ADR 0002 review triggers).

## Review Trigger

Revisit this ADR when: the first three verified vertical slices are complete; Dafny
maintenance cost materially exceeds benefit; compiled Dafny integration is being
considered; the filesystem transport is replaced; or stage boundaries / bounded
contexts materially change.
