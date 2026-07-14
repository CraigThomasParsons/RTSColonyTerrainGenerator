# Migration Roadmap

## Strategy

Use a vertical, incremental migration. Select one narrow behaviour, specify it, verify it, implement it in C#, and place it behind an adapter. Avoid rewriting a complete stage before the workflow is proven.

## Phase 0 — Baseline and Safety Net

### Objectives

- record the existing pipeline behaviour;
- ensure current jobs can still run;
- capture schemas and representative artifacts;
- establish repeatable build and test commands.

### Deliverables

- stage inventory;
- file-format documentation;
- representative golden jobs;
- current stage dependency graph;
- current status-transition map;
- deterministic test seeds;
- artifact hash tool;
- compatibility test harness;
- a root `justfile`.

### Exit Criteria

- one command can run a known job through the current pipeline;
- output artifacts can be inspected and hashed;
- failures are logged by job and stage;
- current behaviour is characterized, even when imperfect.

## Phase 1 — Specification Skeleton

### Objectives

Introduce the new workflow without replacing production stages.

### Deliverables

```text
/docs/product
/features
/specifications
/src/MapGen.Domain
/src/MapGen.Application
/src/MapGen.Contracts
/tests/MapGen.Domain.Tests
/tests/MapGen.AcceptanceTests
```

Add templates for:

- product requirement;
- BDD feature;
- domain contract;
- ADR;
- command/query design;
- verification report.

### Exit Criteria

The first feature can travel from requirement to BDD to contract to Dafny to C# tests.

## Phase 2 — First Vertical Slice: Cell-to-Tile Expansion

### Objectives

Prove the workflow on a small, important, mathematically clear rule.

### Deliverables

- requirement document;
- Gherkin scenarios;
- `CellCoordinate` and `TileCoordinate` value objects;
- Dafny cell-expansion specification;
- verified in-bounds and cardinality properties;
- `ResolveTileRegionCommand`;
- C# domain implementation;
- property-based tests;
- comparison against the current Tiler.

### Exit Criteria

The new implementation agrees with the existing Tiler for selected fixtures or differences are documented and approved.

## Phase 3 — Tile Resolution Context

### Objectives

Migrate the remainder of Tiler behaviour.

### Candidate Rules

- adjacency-mask construction;
- valid terrain-mask combinations;
- tile-set lookup completeness;
- deterministic tile selection;
- dimension expansion;
- artifact schema validity.

### Deliverables

- Tile Resolution bounded context;
- versioned `.maptiles` reader/writer;
- C# stage implementation;
- legacy adapter;
- dual-run comparison mode;
- switchable production implementation.

### Exit Criteria

The C# Tile Resolution stage can replace the legacy Tiler for controlled jobs.

## Phase 4 — Pipeline Lifecycle Context

### Objectives

Make job and stage state transitions explicit and safe.

### Candidate States

```text
Submitted
Ready
Running
Succeeded
Failed
Cancelled
Archived
```

Stage attempts should be separate from the logical stage state so retries remain auditable.

### Verification Candidates

- impossible transitions are rejected;
- a completed stage has a committed artifact;
- an archived job cannot return to running;
- retry creates a new attempt;
- a job cannot report full success if a required stage failed;
- idempotent command handling does not duplicate artifacts.

### Exit Criteria

Pipeline orchestration uses explicit commands and verified transition rules.

## Phase 5 — Heightmap Context

### Objectives

Wrap and then selectively migrate the Rust Heightmap stage.

### First Steps

- document the binary format;
- create a C# reader and validator;
- define dimension and payload-size contracts;
- add deterministic fixture tests;
- retain the Rust generator behind an adapter.

### Verification Candidates

- payload length matches dimensions;
- terrain and height layers align;
- all values are in valid ranges;
- identical inputs produce identical logical output.

The generation algorithm itself may remain in Rust if it is stable and useful.

## Phase 6 — Weather Analysis Context

### Objectives

Specify hydrology outputs and their relationship to the heightmap.

### Verification Candidates

- output dimensions match input dimensions;
- flow directions reference valid neighbours;
- wetness values remain in permitted ranges;
- no missing cells;
- deterministic processing for fixed inputs.

Full physical correctness is not a suitable first formal target. Begin with structural and safety invariants.

## Phase 7 — Vegetation Planning Context

### Objectives

Move deterministic tree-placement rules into explicit domain policies.

### Candidate Rules

- no placement on prohibited terrain;
- placement remains in bounds;
- density limits are respected;
- deterministic random selection uses a defined seed;
- output references valid source artifacts;
- tree types satisfy biome and suitability constraints.

The existing PHP TreePlanter can remain as the initial implementation behind a compatibility adapter.

## Phase 8 — Traversal Context

### Objectives

Build PathFinder as a specification-first component rather than migrating an existing implementation.

### Verification Candidates

- returned path starts and ends correctly;
- every step is adjacent;
- every step is traversable or has an approved infrastructure action;
- path cost is non-negative;
- failure includes an explicit reason;
- generated bridge, stair, ramp, clearing, or ferry actions satisfy placement constraints.

Optimality proofs can be deferred. Begin by proving validity and termination.

## Phase 9 — Operational Consolidation

### Objectives

- standardize stage hosting;
- simplify filesystem orchestration;
- preserve inspectability;
- improve deployment and rollback.

### Deliverables

- C# worker host;
- explicit stage runners;
- health and readiness checks;
- versioned manifests;
- retry and dead-letter strategy;
- push-button deployment;
- rollback plan;
- migration dashboard or CLI status view.

## Suggested Milestone Order

```text
M1  Baseline and golden jobs
M2  Specification templates and CI
M3  Verified cell-to-tile slice
M4  Complete Tile Resolution migration
M5  Verified pipeline lifecycle
M6  Heightmap validation boundary
M7  Vegetation contracts
M8  Traversal built specification-first
M9  Operational consolidation
```

## Rewrite Rule

Do not rewrite a stage merely because it is written in another language.

Rewrite when at least one of the following is true:

- the current implementation blocks required domain changes;
- the behaviour cannot be reliably tested or observed;
- maintenance cost is materially high;
- the language boundary creates operational risk;
- a verified C# implementation provides clear value;
- the team has established compatibility evidence.
