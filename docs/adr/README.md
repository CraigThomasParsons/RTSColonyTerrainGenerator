# Architecture Decision Records

Local ADRs for the RTS Colony Terrain Generator's specification-driven migration,
plus vendored upstream ADRs from The-Pulse that shaped them.

## Local ADRs

| # | Title | Status |
|---|---|---|
| [0001](0001-specification-driven-mapgen.md) | Adopt a specification-driven architecture for map generation (requirement → BDD → contract → Dafny → CQRS/C# → tests) | Accepted |
| [0002](0002-dafny-as-verified-model.md) | Dual-reference design: the Legacy Pipeline as the behavioural baseline, Dafny as the Verified Model; promotion via `specs/dafny-ready.tags` | Accepted |
| [0003](0003-cucumber-js-bdd-runner.md) | cucumber-js as the Gherkin runner (dual profiles legacy/net, personas registry), with a planned Serenity/JS Screenplay evolution | Accepted |
| [0004](0004-ampb-integration-boundary.md) | AgileMedievalPeasantBoard integration boundary: thin HTTP service seam, versioned MapDocument contract in `MapGen.Contracts`, terminal `AgileMedievalExport` stage via the short path; AMPB unchanged | Proposed |

## Vendored upstream ADRs

The files in [`upstream/`](upstream/) are **vendored verbatim** from
`~/Code/The-Pulse` `docs/adr/` (The-Pulse, GitHub `ThePulse-Golf/The-Pulse`),
fetched **2026-07-13**, with only a one-line provenance comment added at the top of
each. Do not edit them here — propose changes upstream and re-vendor.

The **Applies here?** column states each ADR's standing in **this** repo — a
filesystem-pipeline migration to verified C#, not upstream's HTTP/AWS estate.
Categories: **Binding** (rule applies as written), **Adopted** (pattern applies,
with named local adaptations), **Upstream-only** (context, not binding here).

| # | Title | Applies here? |
|---|---|---|
| [0004](upstream/0004-dotnet-modular-monolith-rewrite.md) | Rewrite the backend as a .NET modular monolith (Clean Architecture + CQRS-lite) | **Adopted with adaptations.** The stack cut (Clean Architecture, CQRS-lite on one store, parse-don't-validate, thin handlers) is our model for the C# side. Adaptations: our migration is strangler-style per Slice (upstream rejected strangler-fig; ADR 0001 here adopts it because the legacy pipeline must keep running), and our transport is filesystem lanes, not HTTP. |
| [0010](upstream/0010-modular-monolith-project-structure.md) | Assembly-per-context, two assemblies per module, compiler-fenced boundaries | **Adopted with adaptations.** Shape the C# solution by bounded context (the eight in `CONTEXT.md`), domain assemblies free of infrastructure, SharedKernel kept small, NetArchTest guardrails. Adaptations: contexts and module names are ours (Tile Resolution, Pipeline Lifecycle, …); no EF/tenant concerns — infrastructure assemblies host lane/artifact adapters instead. |
| [0013](upstream/0013-dual-backend-parity-harness.md) | Dual-backend parity with a runnable oracle: Node + .NET side by side, observed and gated ("oracle" is Pulse's term for what we call the Legacy Pipeline baseline) | **Upstream-only, but instructive.** Its stance toward the runnable baseline ("read-only reference truth" — their word for it is "oracle"), committed comparator, and business-key/logical normalization directly inform our dual-reference design — see local [ADR 0002](0002-dafny-as-verified-model.md). The compose/OTel/backend-tag machinery is upstream's HTTP estate and does not bind here. |
| [0014](upstream/0014-upfront-gherkin-parity-suite.md) | Upfront Gherkin parity-suite generation; `net-ready.tags` allowlist; slice tags | **Upstream-only, but instructive.** We keep the slice-tag + committed-allowlist promotion model (`tests/bdd/net-ready.tags`, mirrored formally by `specs/dafny-ready.tags`) and the green-on-the-legacy-baseline-first rule (upstream: "green-on-oracle") — see local [ADR 0002](0002-dafny-as-verified-model.md) and [ADR 0003](0003-cucumber-js-bdd-runner.md). The upfront whole-surface generation work-stream and endpoint crosswalk are not (yet) adopted; contracts are authored per slice. Note its "no Reqnroll" reasoning is necessity-based upstream; ours is reporter-based (ADR 0003). |
| [0015](upstream/0015-ardalis-repository-abstractions.md) | One `IRepository<T>` + Specifications, save-on-mutate, `ITransactionRunner`, "Store" banned | **Adopted.** The persistence vocabulary and rules apply to the C# side as written (one repository abstraction, no per-aggregate wrapper interfaces, Specifications for queries, "Store" banned). Where a slice persists to lanes/artifacts rather than a database, the repository fronts the Artifact Registry port instead of EF. |
| [0017](upstream/0017-ardalis-idiom-set.md) | Ardalis idiom set: Result, FastEndpoints, Vogen, SmartEnum, GuardClauses | **Adopted with adaptations.** Internal idioms apply: `Result<T>` from handlers, Vogen for typed ids/single-value VOs (`JobId`, `Seed`, coordinates), SmartEnum for domain enums, GuardClauses in smart constructors, and the test stack (xunit.v3, NSubstitute, Shouldly). FastEndpoints does not apply (no HTTP edge; our edges are the CLI and lane watchers). Its governing rule transfers intact: when an idiom would change an artifact's wire/file shape, the legacy baseline's shape wins until cutover, and the debt is recorded. |

## Conventions

- One decision per file, numbered `NNNN-slug.md`; local numbering is independent of
  upstream's.
- Status is stated in the file (Proposed / Accepted / Superseded-by link).
- A decision that changes a contract, ledger semantics, or the standing of either
  reference (the Legacy Pipeline baseline or the Verified Model) requires an ADR;
  slice-level design lives in the Spec Pack, not here.
- Vocabulary note: upstream Pulse ADRs say "oracle" for their runnable baseline;
  local docs say "Legacy Pipeline" / "the legacy baseline" (see `CONTEXT.md`).
