# 0005 — Mediator in the application layer

Status: Accepted (2026-07-15)

## Context

Epic 1 (#7) shipped its one command by hand-wiring: `MapGen.Cli` did
`new ResolveTileRegionHandler()` and called `.Handle(...)` directly. That is fine for a
single handler, but it diverges from the reference architecture this programme copies —
The-Pulse v2, whose application layer dispatches every command and query through the
source-generated **Mediator** library returning `Result<T>` (vendored ADR
[upstream/0017](upstream/0017-ardalis-idiom-set.md), the Ardalis idiom set).

As M4 begins, the number of handlers is about to grow (adjacency mask, heightmap reader,
tile-id resolution, full tiling). Introducing the dispatch idiom now — while there is
exactly one handler to retrofit — is far cheaper than after five exist.

## Decision

Adopt **Mediator** (`martinothamar/Mediator`, source-generated, v3) in
`MapGen.Application`:

- Requests implement `IRequest<Result<T>>`; handlers implement
  `IRequestHandler<TRequest, Result<T>>` with the async `Handle(request, ct)` signature.
- A composition root, `AddMapGenApplication()` (`DependencyInjection.cs`), registers
  Mediator and this assembly's handlers. Hosts — the CLI today, the Phase 9 worker host
  later — resolve `ISender` and `Send` commands; they never name a concrete handler.
- Epic 1 is retrofitted onto this shape with identical behaviour (same CLI output, same
  BDD scenarios green on both profiles).

## Why (and the honest caveat)

- **Consistency with the reference architecture** is an explicit goal of the whole
  conversion; the C# side should read like Pulse v2's.
- **Uniform pipeline behaviours.** The real payoff is cross-cutting concerns applied once
  to every request rather than sprinkled through handlers. The first concrete use is
  **request logging** — an `IPipelineBehavior` that logs each command, its outcome
  (`Result` success/failure), and its duration, correlated by job — folding naturally
  into the existing `MapGenStageLogger` conventions. Validation behaviour follows the
  same seam when a slice needs it.
- **Caveat, stated plainly:** upstream leans on Mediator partly for HTTP request
  pipelines (FastEndpoints). Our edges are a CLI and filesystem lane watchers, not HTTP,
  so the pipeline-behaviour payoff is smaller here than there. It is still the right call
  for consistency and for the logging/validation behaviours we will want — but the
  ceremony (async handlers, a service provider at each host) is a real cost we accept
  knowingly, not a free win.

## Enforcement

- `MapGen.ArchitectureTests`: every `*Handler` in the application assembly must implement
  `IRequestHandler<,>` (`Request_handlers_implement_the_mediator_handler_interface`).
- `MapGen.Application.Tests`: `MediatorWiringTests` proves a command sent through `ISender`
  reaches its handler and that failures surface as `Result`, not exceptions.

## Consequences

- New dependencies in the application layer (`Mediator`, `Mediator.Abstractions`,
  `Mediator.SourceGenerator`) and DI abstractions; hosts gain a `Microsoft.Extensions.
  DependencyInjection` reference to build the provider.
- Handlers are now async (`ValueTask`), which the CLI's `Main` became to match.
- Later slices get request dispatch and pipeline behaviours for free; the logging
  behaviour is the first follow-on and can land in its own slice when wanted.
- Reversible in principle (the handlers are plain classes behind an interface), but the
  intent is that this is the standing idiom for the application layer.
