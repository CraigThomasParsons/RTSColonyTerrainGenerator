# Spec-Driven Development for the Map Generation Pipeline

Last updated: 2026-07-13

## Why This Exists

The migration to specification-driven verified C# is bigger than any one
conversation. Chat context is not a reliable source of truth; specs are the durable
handoff. A Spec Pack should be clear enough that a human or a coding agent can pick up
a Slice without needing the originating conversation.

The method follows Kiro-style spec-driven development, extended with the formal lane
this repository adds:

1. Write the product and architecture contract first.
2. Split work into thin, testable slices.
3. Tie every slice to explicit acceptance gates — behavioural (the same Gherkin green
   on both the `legacy` and `net` profiles) and formal (Dafny verification).
4. Keep the spec alive as implementation teaches us something.

## Spec Pack Shape

Every Slice gets a directory `docs/specs/<NN-slice-name>/` (NN = sprint order, e.g.
`01-verified-cell-to-tile`) containing:

- `requirements.md` — what must be true and why: problem, desired behaviour, scope,
  BDD scenarios, and the domain contract.
- `design.md` — the chosen architecture: bounded context, domain model, Dafny level
  and integration pattern, CQRS shape, and legacy adapter boundaries.
- `tasks.md` — implementation slices in execution order, each with its validation
  command.
- `acceptance.md` — the acceptance gates: which Gherkin features must be green on
  which profiles, compatibility evidence against Golden Jobs, and promotion criteria.
- `verification-report.md` — added when Dafny work lands: what was proved, what was
  assumed, what remains unverified.

Templates with per-section guidance live in `docs/specs/templates/`.

## Lifecycle Mapping

Each Spec Pack file carries specific steps of the required feature lifecycle
(`mapgen-spec-driven-planning/03-spec-to-code-workflow.md`):

| Lifecycle step | Where it lives |
|---|---|
| 1. Product requirement | `requirements.md` (Problem, Desired Behaviour, Scope, Acceptance Summary) |
| 2. BDD scenarios | `requirements.md` (scenario list) + `tests/bdd/features/<NN-slice-name>/` |
| 3. Bounded context and domain model | `design.md` (context, aggregate/service, value objects, language) |
| 4. Domain contract | `requirements.md` (preconditions, postconditions, invariants, failures) |
| 5. Dafny model / verified reference | `design.md` (level and pattern) + `specs/**/*.dfy` + `verification-report.md` |
| 6. CQRS design | `design.md` (commands, queries, results, events) |
| 7. C# domain implementation | `tasks.md` (ordered slices) |
| 8. Tests (unit/property/compat/integration/acceptance) | `tasks.md` (per-task validation) + `acceptance.md` (gates) |
| 9. Pull request evidence | `acceptance.md` feeds the PR summary format in `AGENTS.md` |

The Definition of Done in `AGENTS.md` applies to every Spec Pack: same Gherkin green
on both the `legacy` and `net` profiles, Dafny obligations verified, and the slice's
tag appended to
`tests/bdd/net-ready.tags` and `specs/dafny-ready.tags` in the closing PR.

## Review Rules

- Specs are not marketing docs. They must name trade-offs, non-goals, and risks.
- Every public contract must have a validation path.
- Every architectural rule must name its enforcement path, such as an architecture
  test, Dafny obligation, property test, compatibility test against a Golden Job,
  or manual checklist. A rule with no enforcement path is a wish, not a rule.
- If implementation discovers the spec is wrong, update the spec in the same change
  as the code — and classify the work as a `Specification correction`, which requires
  explicit human review (see `AGENTS.md`).
- Contract weakening (preconditions, postconditions, invariants, expected fixtures)
  is never a drive-by edit; it must be named in the PR.

## Current Spec Packs

_None yet. The first will be `docs/specs/01-verified-cell-to-tile/` (see
`mapgen-spec-driven-planning/08-first-epic-verified-cell-to-tile.md`)._

## Source Inputs

- `mapgen-spec-driven-planning/` — the methodology bible (especially 01, 03, 05, 06, 09).
- `docs/Stage_Contract.md` and `MapGenerator/stages.md` — the stage contract and
  current pipeline vocabulary.
- `CONTEXT.md` — the ubiquitous language; use its terms verbatim in every spec.
- `docs/adr/` — decisions binding on all Spec Packs, notably 0001 (the method),
  0002 (dual reference), 0003 (cucumber-js BDD runner).
