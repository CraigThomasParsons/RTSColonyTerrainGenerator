# ADR 0003: cucumber-js as the Gherkin Runner, with a Serenity/JS Screenplay Evolution

- **Status:** Accepted (2026-07-13)
- **Builds on:** ADR 0002 (the legacy baseline this runner drives); upstream
  ADR 0013/0014 (`docs/adr/upstream/`) — the harness shape this mirrors.

## Context

The slice lifecycle needs a Gherkin runner for the acceptance lane: the same feature
file executed against the Legacy Pipeline (the baseline) and against the new C#
implementation.

Upstream The-Pulse chose cucumber-js (ADR 0014) partly out of necessity — an
in-process .NET runner can never drive their runnable Node baseline over HTTP. That
necessity does not exist here: our legacy baseline is CLI-and-files
(`python -m tools.mapgenctl run`, stage lanes), perfectly drivable from .NET. **Reqnroll + Boa Constrictor was seriously
considered**: it would keep one toolchain (everything under `dotnet test`), and Boa
Constrictor ports the Screenplay pattern to .NET essentially 1:1.

It was rejected for two reasons:

1. **The Serenity/JS living-documentation reporter has no .NET equal.** The valued
   end-state (per The-Pulse's Screenplay plan, `docs/plan/serenity-screenplay-personas.md`
   in ThePulseProject, and the Phase 2 worked example in ThePulseVersion2) is Actors
   as personas with Abilities/Tasks/Questions, a Cast provisioned through the app's
   own flows, and above all Serenity's narrated reports that render each run as
   persona journeys — the "Gherkin tests and personas become documentation"
   deliverable. Boa Constrictor covers the pattern but not the narrated living docs.
   By the project's stated rule, the reporter wins the runner decision.
2. **Reusing the Pulse harness verbatim is an explicit project goal.** The
   dual-profile cucumber-js harness (profiles, `world`, personas registry, parity
   normalization helpers) already exists, is proven, and carries the persona pattern
   this repo wants: a named cast defined once as data, referenced by friendly name in
   feature files.

## Decision

Keep **cucumber-js** as the Gherkin runner, mirroring the upstream harness shape:

- Harness at `tests/bdd/`: `features/<NN-slice-name>/`, `steps/`,
  `support/world.js`, `support/personas.js`, with `cucumber.mjs` profiles —
  **`legacy`** drives the legacy pipeline stages, **`net`** drives the new C# CLI —
  exposed as the npm scripts `bdd:legacy`, `bdd:net`, and `bdd:smoke`.
- Personas are registry data in `support/personas.js`, referenced by name in feature
  files (the pseudo-persona pattern upstream shipped), destined to become Screenplay
  Actors.
- Parity normalization compares logical meaning (job ids, dimensions, artifact
  content), never volatile metadata.
- Every feature carries its slice tag (`@slice-NN-<name>`); `tests/bdd/net-ready.tags`
  is the committed allowlist of slices the `net` profile must pass — promotion is a
  reviewed act in the closing PR, alongside `specs/dafny-ready.tags` (ADR 0002).
- **Planned evolution:** Serenity/JS Screenplay at the step layer —
  `@serenity-js/core` + `@serenity-js/cucumber` (+ `@serenity-js/rest` or a
  file/CLI-shaped Ability for the lanes), a Cast built from `personas.js`, Tasks and
  Questions replacing step bodies, and the Serenity reporter emitting living
  documentation as a build artifact. Feature files and tags do not change when this
  lands; it is a step-layer migration only.

## Considered Alternatives

- **Reqnroll (+ Boa Constrictor) under `dotnet test`.** One toolchain, .NET-native,
  Screenplay available — rejected as above: no Serenity-grade living documentation,
  and it discards a working upstream harness this project explicitly wants to reuse.
- **Plain xUnit acceptance tests (no Gherkin).** Rejected: loses the
  non-specialist-readable contract and the persona-narrated documentation entirely.
- **SpecFlow.** Effectively discontinued; Reqnroll is its successor and was the real
  candidate.

## Consequences

- A Node toolchain is added to the repository for the BDD lane.
- The BDD acceptance lane runs via cucumber-js (`npm run bdd:legacy` / `npm run bdd:net`)
  **outside** `dotnet test`; unit, property, architecture, and compatibility tests
  remain xUnit under `dotnet test`. CI and `AGENTS.md` validation lists name both.
- Feature files remain portable Gherkin, written at the behaviour layer in
  CONTEXT.md vocabulary — the decision is reversible: a future runner (Reqnroll
  included) could bind the same features without rewriting them.
- Once ported to the new backend, a slice is promoted in **both** ledgers in its
  closing PR: `tests/bdd/net-ready.tags` (behavioural) and `specs/dafny-ready.tags`
  (formal).
- The Screenplay/living-docs evolution is tracked as its own slice; until then the
  cucumber HTML report is the attached PR evidence.
