# 0006 — GameStart as a React FSD island behind a Laravel BFF

Status: Proposed (2026-07-15)

## Context

This ADR refines the AMPB-facing consumer side of ADR
[0004](0004-ampb-integration-boundary.md). It records a decision about *how the world-gen
setup experience is built inside AMPB*; like 0004, it changes nothing in AMPB today and
nothing in this repository's code — it is the north star the export slice and worker host
build toward.

Facts that shape it:

- **AMPB already runs React.** The map editor is React 19 (`resources/js/editor/
  MapEditor.tsx`), served by Laravel/Blade alongside the Livewire + PixiJS game. So "a
  Laravel page mounts a React island" is an established, shipping pattern in AMPB — not a
  new capability.
- **The-Pulse v2 is the reference shape.** Its client is React organised by Feature-Sliced
  Design (FSD), calling a CQRS .NET backend. Craig wants the AMPB world-setup flow to
  mirror that, so the mental model transfers between the two projects.
- **ADR 0004 keeps MapGen internal.** `MapGen.Api` is never publicly exposed; its only
  clients are trusted server-side callers holding an internal service token.
- **Generation is asynchronous** (ADR 0004): submit → poll/subscribe → collect. The
  setup UI must handle a minutes-long, progress-narrated flow, then hand off to the game.

## Decision

### 1. GameStart is a React (FSD) island, served by Laravel

The world-setup phase — choose seed/parameters, trigger generation, watch progress,
preview the result, start the game — is a self-contained React application, structured by
Feature-Sliced Design, mounted into a Blade/Livewire-served page (the same island pattern
the editor already uses). It is a second island named **GameStart**, not a rewrite of the
game: the rest of AMPB stays Livewire + PixiJS.

### 2. Laravel is the BFF; the browser never talks to MapGen

React GameStart calls **Laravel** endpoints (CQRS-shaped: e.g. `POST /api/worlds`,
`GET /api/worlds/{id}`), and Laravel forwards to `MapGen.Api` with the internal service
token. This preserves ADR 0004's "MapGen never public" rule — the browser has no
knowledge of, and no route to, MapGen. Laravel is the public CQRS edge, which is if
anything *more* faithful to Pulse than exposing MapGen directly: in both cases the React
client talks to a trusted, same-origin backend that owns the session.

Progress reaches the client over AMPB's existing Reverb/Echo channels (a
`world-gen.{jobId}` private channel), so the FSD client subscribes rather than long-polls.

### 3. The handoff to the game is a single navigation, made seamless by pre-loading

When generation completes, the map document is persisted server-side (the `map_documents`
table / `peasant` schema). GameStart then navigates to the Livewire + PixiJS play route
for that game, where the map is already loaded — so the game starts instantly and the one
navigation reads as seamless behind a transition. A true zero-reload merge of a React SPA
and a Livewire page in one runtime is possible but fragile (two frameworks contending for
the DOM and history); the pre-loaded single navigation is the pragmatic seam and matches
how the editor island already behaves.

## Scope and ownership

This is **primarily AMPB-side work** (a React feature, Laravel BFF routes, an Echo
channel). It lives as an ADR in *this* repository because it refines ADR 0004 — the
integration boundary this programme owns — and because the CQRS shape of the Laravel BFF
endpoints should mirror `MapGen.Api`'s contract. The verified-C# conversion is unaffected;
MapGen still just emits a MapDocument through its internal CQRS API.

## Open questions (deferred to when GameStart is actually built)

- **FSD ↔ CQRS mapping granularity.** How closely the Laravel BFF endpoints mirror
  MapGen's commands/queries versus presenting a coarser world-setup facade.
- **Preview rendering.** Whether GameStart renders the map preview in React (a second
  PixiJS/canvas surface) or reuses a shared renderer with the game view.
- **Shared TypeScript contract.** Whether the MapDocument TypeScript type is generated
  from `MapGen.Contracts` (single source of truth) or hand-maintained in AMPB.

## Consequences

- AMPB gains a second React island and a set of BFF routes; the Livewire game and PixiJS
  renderer are untouched. The editor island proves the pattern is viable.
- The security boundary is preserved: MapGen stays internal, tokens stay server-side.
- Craig's two projects converge on one client architecture (React + FSD → CQRS), so
  patterns and tooling transfer between Pulse and AMPB.
- A future decision may generate the MapDocument TS type from `MapGen.Contracts` to keep
  the client and the verified schema in lockstep.
- Until built, this constrains nothing in M1–M5; it only asks that MapGen's CQRS contract
  stay client-consumable (stable, versioned, JSON — already true per ADR 0004).
