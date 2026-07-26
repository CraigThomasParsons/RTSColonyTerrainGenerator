# Deterministic Pipeline Lifecycle Tracer

## Claim

- Gitea Issue: #23
- Status: in progress
- Branch: `feature/23-priority-tracer-deterministic-pipeline-lifecycle`
- Milestone: M5 Verified pipeline lifecycle

## Goal

Prove the cross-project conversion playbook on one narrow, deterministic
pipeline lifecycle without beginning AMPB integration or broad stage migration.

## Preparation

- [x] Compare The Pulse parity loop with Terrain Generator migration rules.
- [x] Define shared and repository-specific conversion invariants.
- [x] Write the bounded priority-tracer specification.
- [x] Create and claim Gitea issue #23.

## Contract Lane

- [ ] Select the pinned legacy command, input, and expected artifact.
- [ ] Author behavior-level BDD without editing target implementation.
- [ ] Prove the contract green against the legacy oracle.
- [ ] Record legacy quirks and suspected defects without repairing them.

## Implementation Lane

- [ ] Record the expected .NET behavioral red state.
- [ ] Implement the smallest application command and artifact boundary with TDD.
- [ ] Add deterministic and artifact-promotion regression coverage.
- [ ] Prove compatibility and declared Dafny invariants.
- [ ] Run `just quality`.

## Independent Exit Lanes

- [ ] Produce a read-only architecture assessment.
- [ ] Review Standards and Spec separately.
- [ ] Remediate confirmed blockers, re-run gates, and re-review.
- [ ] Open a PR without merging it.

## Exact Next Step

Review the `[Contract Seam Proposal]` on Gitea issue #23. It proposes Golden Job
`43860dcf-6469-42a7-9843-4e33abeacfac`, the published legacy Tiler, and its
canonical `.maptiles` hash. After human approval, dispatch a contract-author
lane. Do not author the BDD contract and consume it in the same agent lane.

## References

- `mapgen-spec-driven-planning/13-cross-project-conversion-playbook.md`
- `mapgen-spec-driven-planning/14-priority-tracer-deterministic-pipeline-lifecycle.md`
- `mapgen-spec-driven-planning/03-spec-to-code-workflow.md`
- `docs/adr/0004-ampb-integration-boundary.md`
