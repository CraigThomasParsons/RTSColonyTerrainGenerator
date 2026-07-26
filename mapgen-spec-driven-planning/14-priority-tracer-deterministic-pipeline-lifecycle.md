# Priority Tracer: Deterministic Pipeline Lifecycle

## Status

- Priority: temporary conversion tracer before broader stage migration
- Gitea milestone: M5 Verified pipeline lifecycle
- Gitea issue: #23
- AMPB relationship: architectural north star only

## Why This Moves Forward

Cell-to-tile expansion and tile-resolution primitives have established useful
local correctness. The next test should prove that the conversion method works
across a small pipeline boundary, including contract authorship, legacy parity,
target TDD, artifact safety, architecture assessment, and independent review.

This tracer is promoted for learning. It does not reorder the long-term product
roadmap and does not claim that the full Pipeline Lifecycle context is complete.

## Observable Outcome

Given one pinned legacy input, the legacy pipeline and .NET target produce the
same declared tile-resolution result as a validated deterministic artifact. A
successful run exposes explicit lifecycle state and atomically promotes only a
complete artifact.

## Scope

- Select the smallest existing input that exercises cell expansion and tile
  adjacency or resolution together.
- Record the seed, dimensions, source schema, stage versions, and expected
  lineage.
- Author BDD at the artifact and lifecycle boundary.
- Prove the BDD contract against the existing pipeline before target work.
- Drive a thin .NET application path using the existing domain/application
  projects and Mediator conventions.
- Canonicalize and hash the target artifact.
- Run the same input twice and compare canonical bytes or hashes.
- Validate output before atomic promotion.
- Record explicit success and failure states.
- Run separate read-only architecture and review lanes.

## Out Of Scope

- AMPB source changes.
- The final AMPB `MapDocument` schema.
- `MapGen.Api`, webhooks, progress streaming, or a Laravel BFF.
- Database persistence.
- Replacing Heightmap, WeatherAnalyses, TreePlanter, PathFinder, or Playable.
- General-purpose orchestration or systemd replacement.
- Repairing legacy quirks discovered by the parity contract.

## Contract-Author Lane

The contract author must answer these questions before implementation begins:

1. Which exact legacy command and fixture form the oracle?
2. Which output fields and lifecycle transitions are observable contract?
3. Which values require canonical ordering or normalization?
4. Which invariant is already covered by Dafny?
5. Which legacy quirks must be preserved and separately recorded?
6. What failure proves that partial output is not promoted?

The lane must produce a green oracle run. A missing runnable legacy seam blocks
the slice and becomes a smaller harness issue; it is not invented inside the
implementation lane.

## Target Red State

Before production implementation, the same acceptance contract must fail
against the .NET target for the expected missing behaviour. Infrastructure or
fixture failures do not count as the required red state.

## Target Design Boundary

The expected thin path is:

```text
CLI or acceptance adapter
        -> application command
        -> existing deterministic tile-resolution domain operations
        -> canonical artifact contract
        -> validating temporary writer
        -> atomic promotion
```

Core calculations remain independent from filesystems, clocks, environment
variables, and global random generators. The handler coordinates; it does not
own tile-resolution rules.

## Acceptance Criteria

- [ ] A separately authored BDD contract is green against the pinned legacy
      oracle before .NET implementation begins.
- [ ] The .NET target records an expected behavioral red state.
- [ ] xUnit TDD drives the target to green using the same observable contract.
- [ ] Legacy, Dafny where applicable, and .NET agree on every declared
      invariant.
- [ ] Two target runs from the same pinned input produce an identical canonical
      artifact hash.
- [ ] Input lineage includes seed, dimensions, schema version, and stage
      versions.
- [ ] Invalid or incomplete output remains temporary and is never reported as
      complete.
- [ ] `just quality` passes without rewriting Golden Jobs or weakening a proof.
- [ ] A read-only architecture assessment is recorded.
- [ ] A separate review reports Standards and Spec findings and all confirmed
      blockers are re-gated.
- [ ] No AMPB code or final integration schema is introduced.

## Evidence Table

| Gate | Required evidence |
|---|---|
| Oracle contract | command, exit status, and fixture identity |
| Target red | failing scenario caused by missing target behavior |
| Unit/TDD | focused xUnit command and passing result |
| Dafny | verified file/tag and stated proof boundary |
| Compatibility | legacy and target comparison result |
| Determinism | two-run canonical hash comparison |
| Artifact safety | regression test for validation before promotion |
| Repository | `just quality` result |
| Architecture | read-only assessment artifact |
| Review | Standards/Spec verdict and remediation attempts |

## Follow-On Decision

After this tracer, decide whether to continue Pipeline Lifecycle migration or
first strengthen the shared orchestration tooling. AMPB export remains deferred
until converted artifacts and lifecycle semantics are stable enough to support
a versioned integration contract.
