# Cross-Project Conversion Playbook

## Purpose

The Pulse .NET migration and RTSColonyTerrainGenerator migration are separate
products that deliberately exercise the same engineering method. Lessons may
move between the projects as documented practices and tooling patterns, but
their application code and domain models remain independent.

The shared objective is to make a legacy-to-.NET conversion repeatable:

```text
observe legacy behaviour
        -> author a portable contract
        -> prove the contract against the legacy oracle
        -> drive the .NET target from red to green
        -> run deterministic gates
        -> assess architecture
        -> review standards and specification separately
        -> publish evidence through an issue and PR
```

## Shared Conversion Invariants

1. One issue owns one vertical slice and one feature branch.
2. The legacy implementation is read-only while it acts as the oracle.
3. A contract is proved against the oracle before it drives target code.
4. The contract author and contract consumer are separate work lanes.
5. Target implementation uses TDD and begins from an observed red state.
6. Repository gates, not agent confidence, decide whether a stage advances.
7. Architecture assessment is read-only and cannot silently remediate code.
8. Review evaluates Standards and Spec as distinct concerns.
9. Missing or malformed machine-readable output fails closed.
10. A baseline or Golden Job cannot be changed merely to make a gate pass.
11. Every generative stage is bounded by time, turns, attempts, and cost.
12. Automation may create branches and PRs, but does not merge them.

## Repository-Specific Oracles

The method is shared; the proof obligations are not.

| Concern | The Pulse | RTSColonyTerrainGenerator |
|---|---|---|
| Legacy oracle | Running TypeScript/Express behaviour | Existing stage executable and committed Golden Jobs |
| Portable contract | Gherkin exercised against both HTTP backends | Gherkin exercised against legacy and .NET adapters |
| Inner TDD loop | xUnit domain, handler, and HTTP tests | xUnit domain, application, compatibility, and artifact tests |
| Additional oracle | Database and API parity observations | Dafny model or verified reference implementation |
| Determinism | Request and persistence semantics | Seed, dimensions, canonical artifact bytes, and hashes |
| Main risk | Tenant and data behaviour drift | Mathematical, schema, lineage, and lifecycle drift |

## Required Lanes

### Contract Lane

The contract lane may inspect the requirement and legacy implementation. It
authors observable scenarios and proves them against the legacy oracle. It does
not implement the .NET target for the same slice.

Output:

- approved requirement and scope;
- BDD feature and fixtures;
- recorded oracle command and result;
- documented quirks and suspected defects;
- a machine-readable contract report.

### Implementation Lane

The implementation lane consumes the approved contract. It records the target
red state, uses xUnit TDD, and implements the smallest complete behaviour in the
target architecture. It does not alter the oracle or weaken the contract.

Output:

- red and green evidence;
- production implementation;
- unit, property, compatibility, and acceptance tests as applicable;
- deterministic repository-gate results.

### Architecture Lane

The architecture lane is read-only. It checks ownership, dependency direction,
CQRS boundaries, domain placement, artifact safety, and whether the slice made
an unnecessary abstraction permanent.

Output: an assessment artifact. Any repository mutation stops the lane.

### Review Lane

The review lane uses a separate context from the implementation lane. It reports
Standards and Spec findings independently. Confirmed blocking findings return to
the implementation lane, followed by gates and another review. The retry count
is bounded.

## Terrain Generator Extensions

RTSColonyTerrainGenerator adds the following requirements to the shared loop:

- pin every input seed, schema version, and relevant stage version;
- compare canonical artifacts rather than incidental log text;
- include input lineage and hashes in completion evidence;
- validate temporary output before atomic promotion;
- distinguish example tests, properties, compatibility checks, and proofs;
- state exactly what Dafny proves and what remains outside the model;
- never present a partial artifact as a completed stage result.

## Learning Exchange

After each completed slice, capture only reusable learning under these headings:

1. **Keep** - a practice that worked in both projects.
2. **Adapt** - a practice whose intent transfers but whose implementation differs.
3. **Reject** - a project-specific pattern that should not be copied.
4. **Automate** - a repeated manual check suitable for deterministic tooling.
5. **Escalate** - a contract or architecture decision requiring human approval.

Application code, generated artifacts, domain terminology, and schema decisions
must not be copied across projects merely for consistency.

## Completion Report Contract

Every slice report must include:

- issue, branch, base, and PR;
- requirement and BDD contract paths;
- oracle command and result;
- target red and green evidence;
- Dafny scope and verification result when applicable;
- deterministic gate table;
- architecture assessment path;
- Standards and Spec review counts;
- parity differences and deliberate deferrals;
- exact remaining blocker, or `none`.

CI and independently reproducible gate output outrank an agent's summary when
they disagree.
