<!-- Vendored verbatim from The-Pulse docs/adr/0010-modular-monolith-project-structure.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# .NET modular-monolith project structure: assembly-per-context, two assemblies per module

> **Amended 2026-07-10.** The "flat under `net/`" layout below (`net/Pulse.<Context>/`) was
> superseded before this ADR's ink dried: the solution now emulates the ardalis/CleanArchitecture
> template's own root split, with all module assemblies under **`net/src/Pulse.<Context>/`** and
> all test projects under `net/tests/`. Each module's domain also groups its aggregate, value
> objects, events, and Specifications under one **`Domain/<X>Aggregate/`** folder (e.g.
> `Domain/TenantAggregate/Specifications/`) rather than a flat `Domain/Specifications/` — see
> ADR-0015/ADR-0019 for the Specification-lane decisions this folder shape carries. Both changes
> are cosmetic file-layout moves, not assembly-boundary changes; the per-context module and
> two-assembly decisions below stand unchanged.

The .NET rewrite (ADR-0004) is "Ardalis Clean Architecture organized by the nine bounded contexts" — but the Ardalis template is *layer*-shaped (Core/UseCases/Infrastructure/Web), and four layer-assemblies give **no compile-time isolation between contexts** (PRD #118, story #2 wants the *compiler* to stop one context reaching into another's internals; story #8 wants an arch test on top). So we shape the solution **by context, not by layer**:

- **One module per bounded context**, each split into **two assemblies**:
  - `Pulse.<Context>` — Domain + Application (aggregates, value objects, domain events, command/query handlers, port interfaces). **References no EF Core** — so the compiler enforces the pure domain (parse-don't-validate, ADR-0004).
  - `Pulse.<Context>.Infrastructure` — EF Core configs, repositories, external adapters. References `Pulse.<Context>` + EF Core.
- **`Pulse.SharedKernel`** — DDD base types (`Entity`, `AggregateRoot`, `ValueObject`, `IDomainEvent`) and value objects shared by all contexts (`TenantId`, `Money`, strongly-typed ids). No infrastructure. Every module references it.
- **Cross-context communication is compiler-fenced:** a module has **no project reference** to another module's domain/infra, so it physically cannot see its internals. Contexts talk only via (a) **domain-event notifications** dispatched through Mediator after `SaveChanges` (decoupled side-effects), and (b) a thin **`Pulse.<Context>.Contracts`** assembly (created lazily) holding the public request/event types a context exposes for synchronous cross-context calls.
- **Host** (`Pulse.Api`) is the thin ASP.NET Core composition root: references each module (domain + infrastructure) for DI, composes the Mediator pipeline + Serilog, and registers each module's endpoints. It owns no domain logic.
- **Data ownership:** one `DbContext` **per module** (each owns its tables + EF migrations), sharing the connection/transaction and the per-request tenant-GUC middleware (ADR-0003). Finalized in the data-layer epic (#120).
- **Guardrails (`Pulse.ArchitectureTests`, NetArchTest):** domain assemblies must not depend on EF Core; a module's domain/infra must not be referenced by another module (only its `.Contracts`); the layer direction holds. A violation fails CI (story #8) on top of the compile-time fence (story #2).

## Considered options

- **Four layer-assemblies, contexts as folders** (the literal Ardalis template + my first scaffold) — rejected: no compile-time context isolation; only NetArchTest catches cross-context reach, and the domain folder can `using` EF Core because its assembly references it.
- **One assembly per context (layers as folders inside)** — rejected: loses compile-enforced domain purity (the context assembly references EF Core, so an aggregate can too).
- **Per-context × per-layer assemblies (~36 projects)** — rejected: maximum enforcement, too much ceremony to navigate and build.

## Consequences

- ~2×9 module assemblies + SharedKernel + per-context Contracts (as needed) + host + test projects (~25 projects at full build-out). Worth it for compiler-enforced boundaries on the platform's central maintainability goal.
- Modules are added **one per sprint**, not all up front; the scaffold ships SharedKernel + the host + the arch-test guardrails + one reference module that instantiates the pattern.
- Layout is **`net/src/Pulse.<Context>/`, `net/tests/`** (the ardalis/CleanArchitecture template's own root split, adopted 2026-07-10 — see the amendment above); cosmetic and reversible, unlike the assembly boundaries above.
