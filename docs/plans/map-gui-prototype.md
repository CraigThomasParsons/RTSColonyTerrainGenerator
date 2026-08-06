# Map GUI prototype — MapGen.Api + React/FSD client with Capybara preview

- **Gitea issue:** [#27](http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues/27)
- **Branch:** `feature/27-map-gui-prototype-mapgenapi-reactfsd-client`
- **Status:** In progress
- **Relates to:** ADR [0004](../adr/0004-ampb-integration-boundary.md) (integration
  boundary), ADR [0006](../adr/0006-gamestart-react-fsd-island.md) (GameStart as a
  React FSD island)

## Goal

A working, **local-only** prototype of the map-generation GUI: a React +
TypeScript client structured by Feature-Sliced Design, calling a new
`MapGen.Api` HTTP surface over the existing CQRS handlers, with
`capybara_2d_engine` self-hosted as the map preview renderer.

## Two deliveries, in order

| | Delivery | Client talks to | Lives in | When |
|---|---|---|---|---|
| **Phase 1** (this slice) | Standalone prototype GUI | `MapGen.Api` directly | This repo | Now |
| **Phase 2** | "GameStart" per ADR 0006 | Laravel BFF → `MapGen.Api` | AMPB | After |

The Phase 1 client is **not throwaway**. It is written as FSD feature slices so
the same modules move into AMPB in Phase 2; only the transport swaps (direct API
call → Laravel BFF call).

### Why this does not violate ADR 0004

ADR 0004 requires that `MapGen.Api` is never publicly exposed. The prototype is a
**local dev-only client** — never deployed, never internet-reachable. It exists so
the stack can be validated end to end without waiting on AMPB wiring.

## How this finishes ADR 0006

ADR 0006 (Proposed, 2026-07-15) already specifies React + FSD + CQRS + a Laravel
BFF. It left three open questions, one of which was:

> *"Preview rendering. Whether GameStart renders the map preview in React (a
> second PixiJS/canvas surface) or reuses a shared renderer with the game view."*

**Choosing `capybara_2d_engine` answers that question.** This slice validates the
choice; ADR 0006 should move Proposed → Accepted afterward, recording the answer.

## Architecture

### The backend is .NET

- **`MapGen.Domain` / `MapGen.Application` / `MapGen.Contracts`** — the real
  backend. CQRS handlers, domain rules, DTOs. All C#.
- **`MapGen.Api`** — *does not exist yet*. This slice creates it: an ASP.NET Core
  Web API project that wraps the **existing** `MapGen.Application` CQRS handlers.
  A transport shell; it adds no domain logic. Today the only caller of
  `MapGen.Application` is `MapGen.Cli`, in-process.
- **Laravel (Phase 2 only)** — a **BFF (Backend For Frontend)**: a forwarding
  layer that holds the internal service token server-side so the browser never
  reaches `MapGen.Api` directly. It owns no domain logic.

### Vocabulary (do not conflate)

- **PixelLab** — animated-asset generator. Untouched by this work.
- **capybara.build** — the SaaS that generates consistent static art.
- **`capybara_2d_engine`** — the MIT-licensed engine we self-host. **This is the
  preview renderer.**
- **Pixi.js** — AMPB's current game renderer. Untouched here; whether Capybara ever
  replaces it is a separate, later decision.

## Testing obligation

This slice adds **no domain behaviour**, so the two-reference migration gate does
not apply:

- **Dafny Verified Model: not required.** Nothing here is a mathematical domain
  rule.
- **Legacy-parity BDD: not required.** There is no legacy GUI to be at parity
  with. (Note: in this repository "behavioural test" and "BDD" are the same
  activity — the cucumber-js lane at `tests/bdd/` *is* the behavioural harness.
  For a real domain slice the sequence is `bdd:legacy` green first, then
  `bdd:net`, promoted via `tests/bdd/net-ready.tags`, **plus** Dafny promoted via
  `specs/dafny-ready.tags`.)
- **Normal tests: required.** Real endpoint tests for `MapGen.Api`; fail-first
  tests for the client.

If any phase finds itself needing to change domain behaviour to make the GUI work,
**stop and escalate**. That is a scope breach, not a GUI task.

## Delivery phases

Executed as a supervised `/tmux-pipeline` worker run, one sentinel-gated phase per
freshly cleared context.

| # | Phase | Sentinel |
|---|---|---|
| 1 | Planning doc + wire contract | `PHASE_PLAN_DONE` |
| 2 | Stand up `MapGen.Api` over existing CQRS handlers, with tests | `PHASE_API_DONE` |
| 3a | Client IMPL via `/tdd` | `PHASE_IMPL_DONE` |
| 3b | `/simplify` | `PHASE_SIMPLIFY_DONE` |
| 3c | `/improve-codebase-architecture` + apply worthwhile refactors | `PHASE_ARCH_DONE` |
| 4 | `/code-review` + apply findings | `PHASE_REVIEW_DONE` |
| 5 | Finalize PR to `main` (**never merge**) | `PHASE_PR_DONE` |

## Constraints

- Work only on `feature/27-map-gui-prototype-mapgenapi-reactfsd-client`, in the
  dedicated worktree. **Never** commit to `main`; **never** merge the PR.
- Open the PR on the **first** commit; **push after every commit**.
- Do **not** modify the Legacy Pipeline, Golden Job fixtures, `specs/*.dfy`,
  `tests/bdd/net-ready.tags`, or `specs/dafny-ready.tags`.
- Do **not** touch `/home/craigpar/Code/RTSColonyTerrainGenerator` (the primary
  checkout) — it holds unrelated uncommitted work that must be preserved.
- `MapGen.Api` stays internal: no public exposure, no auth-free routes reachable
  from outside localhost.
- Report any gate that cannot run rather than silently skipping it.

## Acceptance criteria

Tracked on [issue #27](http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues/27).

## Out of scope

- Any change to domain behaviour, Golden Job fixtures, Dafny specs, or promotion
  ledgers.
- Public exposure of `MapGen.Api`.
- The AMPB-side GameStart island and Laravel BFF (Phase 2).
- Solving capybara.build asset export.
