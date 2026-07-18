# AGENTS.md — Agent Operating Manual

This is the operating manual for coding agents working in this repository. It merges
the agent rules from `mapgen-spec-driven-planning/09-agent-operating-rules.md` with the
repository's issue lifecycle, command surface, and dual-reference loop.

Vocabulary is defined in `CONTEXT.md`. Use it everywhere.

## Core Rule

An agent implements reviewed behaviour. It does not silently redefine correct behaviour.

## Project Mission

Convert the legacy multi-language map-generation pipeline, one Slice at a time, into
specification-driven verified C#:

```text
Product requirement
        ↓
BDD scenarios (Gherkin, cucumber-js)
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
Unit, property, integration, compatibility, and acceptance tests
```

Final acceptance target: emit AgileMedievalPeasantBoard's 64×64 map-document JSON
payload from the verified pipeline.

## The Dual-Reference Loop

Every slice is proven against two references (see `docs/adr/0002-dafny-as-verified-model.md`):

1. **The Legacy Pipeline (the baseline).** The slice's Gherkin feature file is
   executed against the running legacy pipeline (`legacy` profile). It must be green
   there first: red against the legacy baseline means the contract is mis-described,
   not that there is a bug to fix. The contract is also grounded in Golden Job
   fixtures captured from the legacy stages' lanes.
2. **The Verified Model (Dafny).** The slice's correctness-critical rules are encoded
   in Dafny under `specs/` (Level A model or Level B verified reference) and must
   verify. The Dafny model states what must hold for all valid inputs, not just the
   fixtures.
3. **The C# implementation must agree with both.** The same feature file goes
   red → green against the new C# implementation (`net` profile); property and
   compatibility tests connect the C# code to the Verified Model and to Golden Job
   fixtures.

**Done for a slice** = the same Gherkin green on both the `legacy` and `net`
profiles, the Dafny obligations
verified, and — in the closing PR — the slice's tag appended to both promotion
ledgers: `tests/bdd/net-ready.tags` (behavioural) and `specs/dafny-ready.tags`
(formal). Promotion is an explicit, reviewable act; do not promote outside the PR.

## Issue Lifecycle (Gitea)

The forge is self-hosted Gitea at `http://192.168.2.48:3000` (owner `craigpars`).
One Slice = one sprint = one Gitea issue = one branch. Milestones are the phases
M1–M9.

- **Start:** `python3 scripts/tools/start_gitea_issue.py <issue-number>` — verifies a
  clean tree, checks the lock file, confirms the issue is open and planned, creates
  `feature/<issue>-<slug>` from `main`, writes the lock, labels the issue
  in-progress, and posts the `[Agent Start]` comment.
- **Single active issue:** the lock file enforces one in-progress issue at a time. If
  the lock names a different issue, stop and report; do not delete the lock.
- **Work:** on the feature branch only. Branch naming is `feature/<issue>-<slug>` —
  never work directly on `main`.
- **End:** `python3 scripts/tools/end_gitea_issue.py --notes <verification notes>
  [--open-pr]` — pushes the branch, optionally opens the PR to `main`, posts the
  `[Agent End]` comment, and releases the lock. Verification notes are mandatory.
- **Park:** `python3 scripts/tools/park_gitea_issue.py [--reason <text>]` — when work
  must pause: checkpoint-commits tracked changes, pushes, updates the lock heartbeat,
  and posts `[Agent Checkpoint]`. Never park with staged or untracked files; resolve
  them first.
- **Never merge to `main`.** Merging is a human act performed through the Gitea PR.

## Repository Command Surface

Run the repository-level commands, not ad-hoc equivalents:

```text
just quality                      # format, build, and static checks across components
dotnet test                       # xUnit: unit, property, architecture, compatibility, integration
dafny verify specs/**/*.dfy       # verify every Dafny specification file
npm run bdd:legacy                # BDD acceptance lane against the legacy pipeline (cucumber-js -p legacy)
npm run bdd:net                   # same features against the new C# implementation (cucumber-js -p net)
npm run bdd:smoke                 # BDD smoke subset against whatever profile is configured
python -m tools.mapgenctl run     # run the legacy pipeline end to end (add --tui for live progress)
```

The BDD acceptance lane is cucumber-js at `tests/bdd/` (`features/`, `steps/`,
`support/world.js`, `support/personas.js`, profiles in `cucumber.mjs`) and runs
outside `dotnet test`; everything else .NET runs under `dotnet test`. See
`docs/adr/0003-cucumber-js-bdd-runner.md`.

## Required Work Order

For a domain-changing feature, the agent must inspect or create artifacts in this order:

1. product requirement;
2. BDD scenarios;
3. bounded-context ownership;
4. domain contract;
5. Dafny specification where required;
6. command/query contracts;
7. C# domain implementation;
8. tests;
9. documentation and migration notes.

Each slice's artifacts 1–4 live in its Spec Pack at `docs/specs/<NN-slice-name>/`;
see `docs/specs/spec-driven-development/README.md`.

## Specification Protection

The agent must not:

- weaken a precondition or postcondition merely to make verification pass;
- replace a meaningful predicate with `true`;
- add `assume` or an axiom without explicit approval;
- remove a failing scenario instead of fixing behaviour;
- alter expected output fixtures without explaining why;
- hide a compatibility difference by normalizing meaningful data;
- move domain rules into handlers, controllers, CLI commands, or infrastructure adapters;
- bypass a value object by passing raw primitives through the domain;
- mark a stage successful before its artifact is committed and validated.

## Change Classification

Before implementation, classify the work as one of:

```text
Behaviour-preserving refactor
New behaviour
Behaviour correction
Specification correction
Infrastructure-only change
Compatibility migration
```

A `Specification correction` requires explicit human review.

## Required Validation

Before presenting work as complete, run the repository-equivalent commands for:

```text
format                  (just quality)
build                   (just quality)
dafny verification      (dafny verify specs/**/*.dfy)
unit tests              (dotnet test)
property tests          (dotnet test)
architecture tests      (dotnet test)
integration tests       (dotnet test)
compatibility tests     (dotnet test)
acceptance tests        (npm run bdd:legacy / npm run bdd:net)
```

When a command cannot run, report:

- the exact command;
- the failure;
- whether the failure existed before the change;
- what remains unverified.

## Pull Request Summary

The agent should produce:

```markdown
## What Changed

## Requirement and Scenarios

## Domain Contract

## Dafny Verification

## CQRS Design

## Tests

## Compatibility

## Promotion
(tags appended to tests/bdd/net-ready.tags and specs/dafny-ready.tags, if the slice closes)

## Risks and Follow-Up
```

## Repository Safety

- work in a feature branch created by `start_gitea_issue.py`;
- do not merge into `main`;
- do not rewrite unrelated files;
- do not delete Golden Job fixtures without approval;
- do not modify binary schemas without a version change;
- preserve backwards-compatible readers during migrations;
- make artifact writes atomic;
- keep stage logs correlated by job and attempt;
- treat the legacy stages as the read-only baseline: run them, capture from them,
  never edit them to make a contract pass.

## Coding Rules

### Domain

- prefer explicit value objects;
- model failures explicitly;
- keep deterministic operations free from clocks, random globals, and filesystem access;
- use injected seed and random abstractions where randomness is intentional;
- keep invariants close to the types that own them.

### Application

- commands mutate or produce effects;
- queries read;
- handlers orchestrate and remain thin;
- validation at the boundary does not replace domain enforcement;
- publish domain or integration events only after successful state changes.

### Infrastructure

- adapters may translate formats but must not redefine domain rules;
- external process failures must be typed and logged;
- temporary files must be distinguishable from committed artifacts;
- validate artifacts before promoting them.

### Tests

- do not test only the happy path;
- use property tests for mathematical rules;
- keep acceptance scenarios understandable — reference Personas by name, define them
  as data in `tests/bdd/support/personas.js`;
- compatibility tests compare logical meaning;
- every corrected bug receives a regression test.
- In JavaScript (steps, support, tooling): never coerce to boolean with `!!`. Say what
  you mean — `Boolean(x)`, an explicit comparison (`x !== undefined`, `x.length > 0`),
  or a real predicate. Craig will protest every `!!` in review.
- In JavaScript: the ternary operator (`? :`) is forbidden — use an explicit `if`
  block so each branch is visually separate and commentable. Full JS rules:
  `docs/style/javascript_node_style.md`.

## Dafny-Specific Rules

- all specification files must verify;
- ghost code may clarify proofs but must not hide missing runtime behaviour;
- loop invariants should state meaningful progress and preserved truth;
- `decreases` clauses must describe real termination;
- any timeout or verification instability must be reported;
- a verified implementation must state what was not proved — record it in the slice's
  `verification-report.md` (template: `docs/specs/templates/verification-report.md`).
