<!-- Vendored verbatim from The-Pulse docs/adr/0014-upfront-gherkin-parity-suite.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# Upfront Gherkin parity-suite generation with a standing oracle re-proof

**Status:** Accepted (2026-07-01). Refines the per-sprint contract authoring described in
`net/docs/plan/bdd-tdd-parity-loop.md`; builds on ADR-0013 (dual-backend parity harness).

The BDD → TDD parity loop originally authored each slice's `.feature` contract at sprint start,
just in time for its implementation. We are instead generating the **entire Gherkin parity suite
upfront** — every in-scope oracle endpoint covered before the implementation agent starts its next
sprint — because the suite's consumer is an autonomous implementation agent that should never be
starved waiting on contract authoring, and because "all of V1's behavior is captured" is only
auditable when the whole surface is mapped at once.

## Decision

- **Generate all slice contracts now**, in sprint order, one PR per slice, each containing the
  slice's feature directory (`tests/bdd/features/<slice>/`), its step definitions, and its rows in
  the endpoint crosswalk. The dual-target cucumber-js harness at `tests/bdd/` (ADR-0013) remains
  the single home — no Reqnroll layer in `net/`.
- **Endpoint crosswalk as the completeness proof.** A generated inventory maps every oracle
  endpoint (~1,350 across `server/`) to either a feature file or an explicit exclusion with a
  reason. Exclusion categories: third-party side effects (QBO, email/SMS delivery, push, payment
  capture — HTTP-visible parts still covered; the external call is .NET integration-test scope),
  background schedulers (not HTTP-triggerable; covered under Hangfire integration tests), and
  Replit-legacy/dead endpoints (never ported).
- **Assertions are domain-visible behavior**: status code, domain-meaningful fields, and side
  effects re-read through the API; error scenarios assert machine-readable codes, never message
  wording. Byte-level response-shape equivalence stays the job of the ADR-0013 comparator lane.
- **Given-state is API-first** on top of the seeded Dragonfly baseline. Both backends' databases
  are seeded by the single `server/seed.ts` path (ADR-0013 §4), so baseline equivalence holds by
  construction; scenarios create everything else through the public API.
- **Rot control without breaching the Actions cost freeze**: contract PRs prove green-on-oracle
  **locally** via a `just` recipe with the cucumber report attached as PR evidence; a single
  **scheduled nightly** Actions run re-proves the full suite against the oracle. Promotion to a
  required per-PR check is the same one-line follow-up ADR-0013 §6 already documents for when the
  freeze lifts.
- **The .NET lane is gated by a committed tag allowlist.** Every feature carries its slice tag
  (`@slice-NN-<name>`); `tests/bdd/net-ready.tags` names the slices the .NET app must pass, and
  each implementation sprint's closing PR adds its tag — flipping a slice red→green is an explicit,
  reviewable act.

## Considered options

- **Just-in-time per sprint (rejected)** — zero drift window, but serializes contract authoring
  into every sprint's critical path and yields no whole-surface completeness view until the end.
- **Hybrid, one phase ahead (rejected)** — smaller batch, but still starves the crosswalk and adds
  a scheduling dependency between two agent work-streams for modest drift savings; the nightly
  oracle re-proof already bounds the drift window to one day.
- **Reqnroll suite in `net/` (rejected)** — .NET-native and fast, but an in-process suite can never
  execute against the Node oracle, which removes the oracle-proving step entirely.
- **Per-PR oracle CI lane now (rejected)** — reverses the documented Actions cost freeze for a
  guarantee the nightly run plus local gates already approximate.

## Consequences

- The implementation agent starts every sprint with its contract already proven green on the
  oracle; sprint "done" remains "same feature green on both backends".
- Features authored for late sprints sit red-on-.NET for months by design; only the allowlisted
  tags gate the .NET lane, and the nightly oracle run keeps every contract honest meanwhile.
- Step definitions ship with the features (a feature that can't execute can't be proven), which
  pulls the shared step vocabulary and bearer-token support in `tests/bdd/support/world.js`
  forward to the start of the work-stream.
- Sprint 17 (BDD Parity Audit, #203) changes character: from "author what's missing" to "run the
  complete suite, close divergences, and reconcile the crosswalk".
- Plan of record for the generation work-stream: `net/docs/plan/parity-contract-generation.md`.
