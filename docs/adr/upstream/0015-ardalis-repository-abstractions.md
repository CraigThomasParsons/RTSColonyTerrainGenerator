<!-- Vendored verbatim from The-Pulse docs/adr/0015-ardalis-repository-abstractions.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# Ardalis.Specification repository abstractions: one IRepository, save-on-mutate, specification queries

**Status:** Accepted (2026-07-01). Applies to the .NET rewrite (`net/`, ADR-0004/0010/0011).

> **Partially superseded by ADR-0016/0017 (2026-07-03) and ADR-0019 (2026-07-03).** Four points below
> change: (1) the **Mediator.Abstractions 2.1.7 pin is retired** (→ 3.x) — it existed to avoid the
> `Ardalis.SharedKernel` package's 3.x drag, but we now *own* the kernel (modeled on Ardalis's source,
> not the package) and choose 3.x deliberately; (2) the **hand-written typed-id / value-object EF
> converters are replaced by Vogen**-generated converters, and the `ValueObject` base is replaced by
> Ardalis's richer one; (3) `IRepository<T>`/`IReadRepository<T>` are now modeled on Ardalis's shapes;
> (4) **the two-query-lanes decision is reversed by ADR-0019** — the Dapper read-service lane is
> retired and reads become projection Specifications through `IReadRepository<T>`, with EF `SqlQuery`
> as the exception-only hand-SQL escape hatch (the "Specifications everywhere" option rejected below
> is now taken, its RLS and escape-hatch objections answered there). **What stands:** "own your
> kernel, not the package" is *upheld*, and the write-side repository decision (one `IRepository<T>`,
> no per-aggregate wrappers, save-on-mutate + `ITransactionRunner`, "Store" banned) is unchanged.

Two slices into the Platform Admin migration, aggregate persistence had already drifted: one module
holds `ITenantStore`, `IUserStore`, and `IOperatorRepository` side by side (two names for the same
concept), and two transaction dialects coexist — Platform Admin stages writes and commits once via
`IUnitOfWork`, while Identity's `RefreshTokenStore` owns its own `SaveChangesAsync`. Every new
aggregate costs a hand-written port + adapter pair, and nothing rules on the vocabulary (ADR-0010
casually says "repositories"; the code says mostly "Store"). Left alone, each agent imitates
whichever example it happens to read.

## Decision

Standardize aggregate persistence on the **Ardalis.Specification** repository abstractions, with
thin markers of our own:

- **Packages:** `Ardalis.Specification` 9.3.1 (dependency-free on net8.0) referenced by
  `Pulse.SharedKernel`; `Ardalis.Specification.EntityFrameworkCore` 9.3.1 (EF Core ≥ 8.0.19; we ship
  8.0.28) referenced by `Pulse.SharedKernel.Infrastructure`. **Not** the `Ardalis.SharedKernel`
  package — it drags `Mediator.Abstractions` 3.x (we pin 2.1.7) and duplicates our `Primitives.cs`
  base types. To be explicit about ADR-0010: the Ardalis template's *layer layout* stays rejected;
  this adopts only its *persistence abstraction*.
- **Markers:** `IRepository<T> : IRepositoryBase<T> where T : class, IAggregateRoot` in
  `Pulse.SharedKernel`; one generic `Repository<T, TContext> : RepositoryBase<T>, IRepository<T>` in
  `Pulse.SharedKernel.Infrastructure`; each module registrar adds one closed registration per
  aggregate root, bound to its own DbContext (whose connection carries the tenant GUC + role).
  No `IReadRepository<T>` (added only when a real read-intent case appears) and **no per-aggregate
  wrapper interfaces** — a custom query need is met by a new Specification, never a new interface.
- **Save semantics: upstream save-on-mutate is kept.** `AddAsync`/`UpdateAsync`/`DeleteAsync`
  persist immediately, exactly as the Ardalis ecosystem documents — fidelity to the pattern agents
  already know beats a local dialect. Mutations to a tracked aggregate flush with that context's
  next save. A handler making **two or more repository writes** wraps them in the per-context
  **`ITransactionRunner.InTransactionAsync`** port, which replaces `IUnitOfWork` (the
  stage-everything-commit-once enrollment contract is retired). `IAuditTrail` becomes self-saving
  (`RecordAsync`).
- **Two query lanes.** Command handlers query aggregates only through `IRepository<T>` +
  **named Specifications** in the owning context's `Domain/Specifications/` (they encode domain
  predicates and the core package is EF-free, so the domain fence holds). The read side keeps the
  sanctioned Dapper read-service lane on the request's RLS-pinned connection, unchanged. The write
  side never uses a read service; the read side never uses a repository.
- **Precondition: the aggregate is the EF-mapped type.** `RepositoryBase<T>` requires
  `DbContext.Set<T>()`, so the adoption-row translation stores cannot host it. Tenant, User, and
  Operator are therefore refined to direct domain mapping **now** (ADR-0011's own
  placeholder-refinement step, front-loaded): typed-id/value-object converters, `PersonName` as a
  two-column complex mapping, `Ignore(DomainEvents)` per the `RefreshTokenConfiguration` precedent,
  and **shadow properties for every adopted-only column** carrying the scaffolded configuration —
  the relational model must not change (the ADR-0011 no-op-diff guard is the gate). The stores'
  hand-written default lines (`OnboardingAnswersJson = "{}"`, `PersonType.Employee`,
  `EmploymentStatus.Inactive`) move into EF configuration where the oracle's own column defaults
  take over.
- **Vocabulary:** "Repository" is canonical; "Store" is banned for persistence gateways (the
  PR #296 rename toward `TenantStore` is judged local drift, not vocabulary — and "Store" collides
  with ASP.NET Identity's `IUserStore`). Glossary in root `CONTEXT.md` § Persistence language.
- **Enforcement:** architecture tests — a class depending on a module DbContext must not be named
  `*Store`, and `IRepositoryBase`-assignable types may be declared only by the SharedKernel pair —
  plus a DI-completeness test asserting every `AggregateRoot`-derived type resolves an
  `IRepository<T>` from the composed host. Agent-facing rules land in `net/AGENTS.md`,
  `csharp_style.md`, `dotnet_target_architecture.md`, and `migration-agent-prompt.md`.

## Considered options

- **Hand-rolled minimal `IRepository` (no package)** — rejected: without specifications every
  non-trivial query breeds a bespoke port method, which is exactly the boilerplate/drift surface
  being eliminated; we would re-own evaluator maintenance to get it back.
- **`Ardalis.SharedKernel` wholesale** — rejected on facts: `Mediator.Abstractions` 3.x conflict and
  duplicate DDD base types.
- **Override to stage + `IUnitOfWork` commit** — the strongest alternative (it preserves
  ProvisionTenant's one-transaction shape with zero wrapping) but rejected: it forks the documented
  Ardalis contract that agents are pretrained on, and the drift this ADR exists to kill starts with
  local dialects. The explicit `ITransactionRunner` wrapper restores multi-write atomicity visibly.
  The feared `users↔tenants` FK cycle turned out not to exist at the row level: the tenants table
  itself carries no FK to users (the user-referencing columns live on child tables such as
  tenant_module_settings and tenant_onboarding_checklists), so the natural insert order - tenant,
  then users - is FK-safe across separate saves with no choreography.
- **Specifications everywhere (retire Dapper reads)** — rejected: rewrites the sanctioned,
  RLS-annotated read lane the style guide names "the model to copy" and loses the hand-SQL escape
  hatch oracle parity relies on.
- **Keep translation stores under the new interface** — rejected as technically broken:
  specifications evaluate against the EF model, so specs written on domain types cannot translate
  through an adoption-row seam; hand-implementing the 15-method `IRepositoryBase` per aggregate
  multiplies boilerplate instead of deleting it.
- **`IStore<T>` as the canonical name** — rejected: renames the concept away from ADR-0010's own
  wording, the base interfaces the code visibly extends, and the ecosystem documentation agents read.

## Consequences

- Four ports and their adapters (`ITenantStore`, `IUserStore`, `IOperatorRepository`,
  `IRefreshTokenStore`) are deleted; a new aggregate now costs one DI registration line, not an
  interface + implementation pair. Both transaction dialects collapse into one rule.
- `ProvisionTenant` wraps its writes in `ITransactionRunner`; domain events dispatch per save rather
  than once per business operation — event handlers must tolerate mid-operation dispatch (an outbox
  is the eventual fix if cross-context handlers ever read uncommitted siblings).
- The refactor is gated by the parity contracts, `parity-smoke` (real RLS), and the no-op-diff
  guard; the adopted-column knowledge in store comments survives as EF configuration.
- Future contexts (#124–#133) arrive with direct-mapped aggregates from day one; the refinement cost
  paid here is not paid again.
- Indexed in `net/AGENTS.md`.
