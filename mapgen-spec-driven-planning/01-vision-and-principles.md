# Vision and Principles

## Vision

The Map Generation Pipeline will become a system in which important behaviour is defined before implementation and can be checked by multiple forms of evidence.

A feature is considered complete only when:

- the intended product behaviour is written clearly;
- representative examples exist as BDD scenarios;
- domain terms and ownership are explicit;
- critical invariants are captured as contracts;
- the implementation conforms to the contracts;
- automated tests protect integration and user-visible behaviour;
- the CI pipeline rejects specification weakening and unverified changes.

## Primary Objectives

### 1. Make agent-generated code safer

Agents should work against contracts rather than broad prose alone. Their job is to produce an implementation that satisfies existing constraints, not reinterpret the domain on every change.

### 2. Make domain behaviour visible

Rules such as determinism, valid terrain placement, path validity, job-state transitions, and resource conservation should be discoverable without reading implementation details.

### 3. Support incremental replacement

Rust, PHP, Python, Kotlin, and C# components should be replaceable gradually. The migration must not require an immediate full rewrite.

### 4. Make failure explicit

Stages should return typed success or failure results. A stage must not silently lose a job, partially write an artifact, or report success without satisfying its postconditions.

### 5. Improve reproducibility

Given the same versioned inputs, seed, configuration, and stage versions, the logical output should be reproducible.

## Guiding Principles

### Specification before implementation

A meaningful behavioural change begins in the requirement, examples, and contract. Production code follows.

### Ubiquitous language

The same domain terms should appear in product requirements, Gherkin scenarios, Dafny models, C# types, logs, and pull requests.

Examples:

- `MapGenerationJob`
- `HeightmapArtifact`
- `TileMapArtifact`
- `TerrainCell`
- `ResolvedTile`
- `VegetationPlan`
- `TraversalPath`
- `StageAttempt`
- `PipelineFailure`

### Invariants live in the domain

Controllers, handlers, file watchers, and message consumers may orchestrate work, but they must not be the only location where domain rules exist.

### CQRS expresses use cases

Commands change state or create artifacts. Queries inspect existing state or artifacts. Command handlers coordinate domain services and repositories but should remain thin.

### Dafny is selective

Use Dafny for rules where exhaustive reasoning is valuable:

- coordinate transformations;
- dimensional consistency;
- determinism contracts;
- state-transition validity;
- path validity;
- conservation rules;
- ordering and dependency rules;
- duplicate and idempotency rules.

Do not force Dafny into ordinary infrastructure code.

### Tests and proofs serve different purposes

Proofs show that an implementation satisfies a formal statement for all valid inputs.

Tests show that systems, adapters, files, frameworks, and user-visible workflows behave correctly in representative environments.

Both are required.

### No big-bang rewrite

The current pipeline remains operational during migration. Compatibility is protected with characterization tests, golden files, schema checks, and dual-run comparisons.

## Non-Goals

This plan does not attempt to:

- formally verify every line of the application;
- replace BDD with theorem proving;
- place all pipeline stages into one bounded context;
- place all logic in command handlers;
- rewrite every stage in C# immediately;
- remove the filesystem transport before an alternative is proven necessary;
- prove visual quality or game-design fun through Dafny;
- allow an agent to change specifications without review.
