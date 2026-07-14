<!-- Vendored verbatim from The-Pulse docs/adr/0004-dotnet-modular-monolith-rewrite.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# Rewrite the backend as a .NET modular monolith (Clean Architecture + CQRS-lite)

The Express/Node backend (`server/routes.ts` ~55k lines, `server/storage.ts` ~11k lines, `shared/schema.ts` ~9k lines, ~1,295 route handlers, ~15 in-process schedulers) is being replaced — not refactored in place — by a single-deployable **.NET modular monolith** using ardalis Clean Architecture, organized by the nine product bounded contexts in `CONTEXT-MAP.md`. We chose this over the original Phase 5 plan (split the big TypeScript files in place) because file-splitting delivers neither enforced domain boundaries, type-driven correctness, nor the Phase 1–4 operational properties; and over an incremental strangler-fig because the owner wants one clean stack cut over at parity, not two backends coexisting. The React frontend and PostgreSQL (with RLS) are fixed points; only the server and its schedulers change.

## Considered options

- **In-place TS refactor** (original Epic #43) — rejected: cosmetic; no boundary enforcement, no static-type guarantees, no scheduler/scale fix.
- **Strangler-fig incremental migration** — rejected: long-lived dual-backend complexity and routing for a single-tenant-heavy app the owner would rather rebuild once.
- **Microservices** — rejected: chosen Mediator-for-**intraprocess** messaging implies one process; network boundaries buy nothing here.
- **Full CQRS with a separate read store** (the MS CQRS doc) — rejected in favor of **CQRS-lite on one Postgres**: command/query handler separation without eventual-consistency cost.

## Consequences

- **This is the most expensive, least-reversible decision in the roadmap.** It supersedes the "V2 is TypeScript" assumption in `docs/REBUILD_STRATEGY.md` — that document's two-track model still holds, but the V2 track is now .NET.
- Phase 1–4 hardening **cannot be inherited** by a greenfield backend; the .NET epics re-absorb security/observability/scalability/portability as native acceptance criteria, while Phases 1–4 keep hardening the live V1 in parallel.
- Stack choices that now carry lock-in: **EF Core** owns DDL (Drizzle retired; first migration baselines the existing schema — no data migration), **martinothamar Mediator** (the free/source-generated alternative to the now-commercial MediatR; ardalis's MediatR-based template is adapted to substitute it), **FluentValidation** at the edge only, **Hangfire** (Postgres) for time-triggered jobs with distributed locking, **Serilog** (+ Sentry sink).
- **Parse-don't-validate is a standing rule, not a style preference:** domain invariants live in value-object smart constructors; commands carry already-parsed value objects; handlers do near-zero validation. Don't "add validation" back into handlers — if a rule isn't cross-field shape (FluentValidation at the edge), it belongs in a type.
- RLS survives the swap only because a per-request middleware sets the tenant GUC from the JWT tenant claim; see ADR-0003. Forgetting that middleware silently disables tenant isolation.
