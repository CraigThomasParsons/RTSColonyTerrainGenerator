# Map Generation Pipeline — Specification-Driven Migration Plan

## Purpose

This planning pack describes how to migrate the existing filesystem-driven Map Generation Pipeline toward a specification-driven architecture using:

1. Product requirements
2. BDD scenarios
3. Domain contracts
4. Dafny models and proofs
5. Domain-Driven Design
6. CQRS
7. C# production implementations
8. Integration and acceptance tests

The goal is not to rewrite the entire pipeline at once. The goal is to introduce a repeatable workflow in which each important domain rule becomes:

- understandable to a product owner;
- expressible as executable examples;
- captured as a formal contract;
- verified where practical;
- implemented through explicit commands and queries;
- protected by automated tests and CI quality gates.

## Target Development Flow

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
Unit, integration, and acceptance tests
        ↓
Observed production behaviour and feedback
```

DDD is not a single step after the specification. It shapes the language, ownership, boundaries, and invariants throughout the process.

CQRS is not simply a folder layout. It provides explicit use cases through commands and queries and keeps orchestration separate from domain rules.

Dafny is used selectively for correctness-critical rules. It is not required for controllers, file watching, logging configuration, dependency injection, or other framework plumbing.

## Current Pipeline

The current system contains or plans the following stages:

| Stage | Current implementation | Responsibility |
|---|---|---|
| Heightmap | Rust | Deterministic terrain height generation |
| WeatherAnalyses | Rust | Hydrology, flow accumulation, and wetness |
| Tiler | C# | Convert cells into resolved tiles |
| TreePlanter | PHP | Deterministic vegetation placement |
| WorldFeatures | Planned | Add natural and world features |
| PathFinder | Planned Kotlin | Ensure traversal and infrastructure access |
| Orchestration | Python, systemd, filesystem | Submit, watch, route, archive, inspect, and log jobs |

## Recommended Migration Strategy

Use an incremental strangler approach:

1. Preserve the existing file formats and stage boundaries.
2. Introduce specifications around one rule at a time.
3. Add C# contracts and adapters around existing stages.
4. Replace a stage only after its behaviour is characterized.
5. Maintain compatibility tests between old and new implementations.
6. Retire legacy implementations only after verified parity and operational confidence.

## Documents

- `01-vision-and-principles.md` — goals, non-goals, and operating principles.
- `02-target-architecture.md` — bounded contexts, layers, CQRS, and component relationships.
- `03-spec-to-code-workflow.md` — the required lifecycle for a feature.
- `04-migration-roadmap.md` — phased migration plan.
- `05-bounded-contexts-and-ownership.md` — proposed domain boundaries for the pipeline.
- `06-dafny-verification-strategy.md` — what to verify and how to avoid false confidence.
- `07-ci-quality-gates.md` — quality gates for agents and human contributors.
- `08-first-epic-verified-cell-to-tile.md` — the first concrete implementation epic.
- `09-agent-operating-rules.md` — constraints for coding agents.
- `10-adr-001-specification-driven-mapgen.md` — architecture decision record.

A combined version is also included as `MapGen-Spec-Driven-Planning-Bible.md`.
