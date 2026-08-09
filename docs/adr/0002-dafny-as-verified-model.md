# ADR 0002: Dafny as the Verified Model in a Dual-Reference Design

- **Status:** Accepted (2026-07-13)
- **Builds on:** ADR 0001 (specification-driven lifecycle); upstream ADR 0013/0014
  (`docs/adr/upstream/`) for the single-reference parity model this extends.
- **Detail:** `mapgen-spec-driven-planning/06-dafny-verification-strategy.md`.

## Context

The-Pulse proves each slice's contract against a single runnable reference: the Node
backend, which its docs call the "oracle" (upstream ADR-0013/0014 use that word
throughout; this repository's docs do not — see `CONTEXT.md`, "Legacy Pipeline"). A
Gherkin feature green against that baseline means the contract is captured correctly;
the same feature going green on .NET means the slice is ported. That model answers
one question well — *what does the system do today?* — and its answer is only as
strong as the scenarios and fixtures exercised.

This repository has the same need (the legacy stages are the runnable truth of
current behaviour) plus one The-Pulse does not: many map-generation rules are
mathematical — cell-to-tile expansion, dimensional consistency, bounds, uniqueness,
determinism, path validity, state-transition validity, conservation. Example-based
evidence cannot cover all valid coordinates, dimensions, and transitions, and a
coding agent can satisfy fixtures while violating the rule elsewhere in the input
space. A second reference is needed to answer *what must always be true, for all
valid inputs?*

## Decision

Every migrated slice is held to **two references**, and its C# implementation must
agree with both:

1. **The Legacy Pipeline (the baseline).** The legacy stages are the executable
   specification of current behaviour, exactly the stance The-Pulse takes toward its
   Node backend: read and run freely, never modify. Evidence lanes: the slice's
   Gherkin features proven green against the legacy pipeline (`legacy` profile,
   ADR 0003), and compatibility tests replaying Golden Job fixtures captured from the
   stages' lanes.
2. **The Verified Model (Dafny).** The slice's correctness-critical rules are encoded
   under `specs/` as a Level A executable mathematical model or a Level B verified
   reference implementation (per planning doc 06), and all proof obligations must
   discharge under `dafny verify`. Level A (independent model checked via property
   tests) is the default; Level B (canonical fixture outputs compared by
   compatibility tests) is used when replacing a legacy stage where exact behavioural
   parity matters; Level C (compiled Dafny) requires its own decision.

The two references are deliberately different in kind and can disagree. When they do,
the disagreement is a finding, not a nuisance: either the legacy stage has a bug
(a `Behaviour correction`, decided by a human) or the model mis-states the rule
(a `Specification correction`, also human-reviewed). Neither reference is silently
"fixed" to match the other.

**Promotion is an explicit, reviewable act.** A slice's formal standing is recorded
by appending its tag to `specs/dafny-ready.tags` in the closing PR — CI requires the
listed slices' Dafny obligations to verify from then on. This mirrors The-Pulse's
`tests/bdd/net-ready.tags` allowlist (upstream ADR 0014), which this repository also
keeps for the behavioural lane: a closing PR promotes into both ledgers.

Each verified component ships a verification report
(`docs/specs/templates/verification-report.md`) stating what was proved, what was
assumed, and what remains unverified. The specification-protection rules in
`AGENTS.md` (no weakened `requires`/`ensures`, no unapproved `assume`/axioms) are the
guardrails that keep the Verified Model honest.

## Considered Alternatives

- **Single reference (legacy stages only), The-Pulse style.** Rejected: sufficient
  for CRUD-shaped behaviour, insufficient for universal mathematical rules; fixtures
  under-constrain agents.
- **Dafny as the only reference.** Rejected: the legacy stages embody accumulated,
  undocumented behaviour (formats, quirks, fan-out) that a fresh formal model would
  silently drop; formal models can be wrong, and the runnable pipeline is the check.
- **Property-based tests instead of Dafny.** Kept, but as a bridge, not a substitute:
  property tests sample the input space; proofs cover it. Properties are drawn from
  the Dafny contracts so the two stay aligned.
- **Verify everything in Dafny.** Rejected per ADR 0001: selective use only; no
  systemd, CLI parsing, serialization, or rendering proofs.

## Consequences

- Two references means two failure surfaces per slice; the workflow (Spec Pack →
  contract → Dafny → C#) sequences them so each failure is attributable.
- `dafny` joins the toolchain and CI (`dafny verify specs/**/*.dfy`); verification
  time and prover instability become CI concerns and must be reported, not retried
  into silence.
- Golden Job fixtures become protected assets (deleting or regenerating them is a
  specification change).
- The legacy stages must remain runnable (`python -m tools.mapgenctl run`) until the
  last slice depending on them is promoted.
- When the two references disagree, migration pauses on that rule until a human
  classifies the difference — slower, and the point.
