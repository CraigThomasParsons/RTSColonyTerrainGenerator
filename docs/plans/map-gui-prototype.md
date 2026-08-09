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

## Wire Contract

This section is the output of Phase 1 and the input to Phases 2 and 3a. It fixes
exactly how the React client talks to `MapGen.Api`. No C# or TypeScript is written
here; both sides are held to this section.

### What already exists (grounding)

Read before trusting anything below:

| Source | What it fixes |
|---|---|
| ADR [0004](../adr/0004-ampb-integration-boundary.md) §1 | The three world endpoints and the submit → poll → collect shape |
| ADR 0004 §2, §4 | `MapDocument` is versioned in `MapGen.Contracts` and carries `seed`, `generator_version`, `job_id` |
| `src/MapGen.Application/TileResolution/` | The only two CQRS handlers that exist today: `ResolveTileRegionCommand`, `ComputeAdjacencyMaskCommand` |
| `src/MapGen.Application/Common/Result.cs` | Handlers return `Result<T>` — `IsSuccess` / `Value` / `Error`, failures are strings, never exceptions |
| `tests/fixtures/golden/*/input.job.json` | The real job-spec vocabulary: `job_id`, `map_width_in_cells`, `map_height_in_cells`, `requested_at_utc` |
| `tests/fixtures/golden/*/*.playable.json` | `version`, `job_id`, `start_zones[]`, `resource_clusters[]`, `settlement_labels[]` |
| `docs/baseline/artifact-formats.md` | `.worldpayload` terrain vocabulary: `deep_water, water, dirt, grass, rock, mountain`; `.maptiles` header |
| AMPB `storage/app/maps/*.json` | The map-document vocabulary the export must match, on a 64×64 grid |
| `MapGenerator/stages.md` | The stage names a progress response may report |

**`MapGen.Contracts` is empty today.** It contains exactly one file,
`ContractsAssembly.cs`, an assembly anchor with no types. So "prefer reusing
existing `MapGen.Contracts` types" resolves to: there are none, and every DTO named
below is new *to that assembly*. What each one must **not** do is invent vocabulary:
each is a C# projection of an already-observed shape (a golden-job spec, a
`.playable.json`, an AMPB map document, an existing command record). Genuinely new
invention is called out explicitly and justified in
[New DTOs and why](#new-dtos-and-why).

### Generation is asynchronous

**Submit → poll or subscribe → collect.** This is not an implementation detail the
client may paper over; it is fixed by ADR 0004 ("a pipeline run crosses many stages
and languages (seconds to minutes), so a blocking 'New Game' HTTP call is not
viable") and restated by ADR 0006.

```
POST /worlds                      -> 202 Accepted  { job_id, status: "queued" }
GET  /worlds/{job_id}             -> 200           { status, stage, pct, ... }   (repeat)
GET  /worlds/{job_id}/map-document -> 200          MapDocument                    (once succeeded)
GET  /worlds/{job_id}/preview      -> 200          MapPreview                     (once succeeded)
```

Consequences the client must honour:

- `POST /worlds` returns **202**, never the map. A client that awaits a map from the
  submit call is wrong.
- The collect endpoints return **409 Conflict** while the job is not `succeeded`, so
  a premature collect is a distinguishable error, not a 404 and not a hang.
- **Phase 1 polls.** ADR 0004 leaves push-vs-poll open and ADR 0006 resolves it
  *for AMPB* (Reverb/Echo). The standalone prototype has no Reverb, so it polls
  `GET /worlds/{job_id}` at a fixed interval (**1000 ms**, with the interval a client
  config value). The client isolates polling in a single FSD `entities/world` model
  so Phase 2 can swap it for an Echo subscription without touching any feature slice.
- Terminal states are `succeeded`, `failed`, `cancelled`. The client stops polling on
  all three.

### Endpoints

Base path `/api/v1`. All request and response bodies are `application/json` in
**`snake_case`** — the MapDocument must be snake_case because AMPB consumes it
verbatim, and one convention across the whole surface beats a mixed one.

#### World generation (async)

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/worlds` | Submit a generation job | `202` + `JobAccepted` |
| `GET` | `/worlds/{job_id}` | Poll job status | `200` + `JobStatus` |
| `GET` | `/worlds/{job_id}/map-document` | Collect the AMPB payload | `200` + `MapDocument` |
| `GET` | `/worlds/{job_id}/preview` | Collect the renderable preview | `200` + `MapPreview` |
| `DELETE` | `/worlds/{job_id}` | Cancel an in-flight job | `202` + `JobStatus` |
| `GET` | `/worlds` | List recent jobs (dev convenience) | `200` + `JobStatus[]` |

`DELETE` and the list endpoint are prototype affordances, not part of ADR 0004's
contract; Phase 2 may drop them without a version bump. They are marked as such in
the OpenAPI document.

#### Tile resolution (synchronous)

These wrap the two handlers that **actually exist**, unchanged. They are the only
endpoints in this slice backed by real verified domain code, and they are what the
Phase 2 endpoint tests can assert real behaviour against.

| Method | Path | Wraps | Success |
|---|---|---|---|
| `POST` | `/tiles/expand-cell` | `ResolveTileRegionCommand` | `200` + `TileRegionResponse` |
| `POST` | `/tiles/adjacency-mask` | `ComputeAdjacencyMaskCommand` | `200` + `AdjacencyMaskResponse` |

`POST` rather than `GET` because `adjacency-mask` carries a row-major terrain array
that does not belong in a query string; `expand-cell` matches it for symmetry.

### Request and response shapes

#### `POST /worlds` — request (`GenerateWorldRequest`)

```json
{
  "seed": 1234567890,
  "map_width_in_cells": 64,
  "map_height_in_cells": 64,
  "name": "Default Forest"
}
```

- `map_width_in_cells` / `map_height_in_cells` — **the same names as
  `input.job.json`.** Not `width`/`height` as ADR 0004's sketch abbreviates them:
  the golden-job spec is the shape that actually exists, and cells-vs-tiles ambiguity
  is precisely the confusion ADR 0004's open "resolution mapping" question is about.
- `seed` — optional, `int64`. Omitted means the server picks one and echoes it back;
  determinism (ADR 0004 §4) requires the client always learn the seed it got.
- `name` — optional, human label. Slug is derived server-side.
- ADR 0004's `params` bag is **deliberately not in v1**. There are no generator
  parameters in the golden-job spec to populate it with, and an empty
  `Dictionary<string, object>` on the wire is an invitation to smuggle
  unversioned vocabulary across the seam. It is added when a real parameter exists.

Validation failures return `400` with the error envelope below.

#### `POST /worlds` — response (`JobAccepted`)

```json
{
  "job_id": "43860dcf-6469-42a7-9843-4e33abeacfac",
  "status": "queued",
  "seed": 1234567890,
  "submitted_at_utc": "2026-01-28T00:42:24Z"
}
```

Plus a `Location: /api/v1/worlds/{job_id}` header.

#### `GET /worlds/{job_id}` — response (`JobStatus`)

```json
{
  "job_id": "43860dcf-6469-42a7-9843-4e33abeacfac",
  "status": "running",
  "stage": "Tiler",
  "pct": 37,
  "seed": 1234567890,
  "map_width_in_cells": 64,
  "map_height_in_cells": 64,
  "submitted_at_utc": "2026-01-28T00:42:24Z",
  "completed_at_utc": null,
  "error": null
}
```

- `status` — one of `queued`, `running`, `succeeded`, `failed`, `cancelled`.
  Lowercase strings on the wire, never integers; a C# enum ordinal is not a contract.
- `stage` — a stage name from `MapGenerator/stages.md` (`Heightmap`,
  `WeatherAnalyses`, `Tiler`, `TreePlanter`, `WorldFeatures`, `PathFinder`,
  `AncientCivilization`, `Playable`, `AgileMedievalExport`), or `null` when `queued`.
  The client treats it as an opaque display string — it must not branch on stage
  names, because the stage list is legacy-pipeline vocabulary that will change as
  the .NET conversion proceeds.
- `pct` — integer 0–100, monotonically non-decreasing within a job. Advisory only.
- `error` — non-null **iff** `status` is `failed`; carries the `Result<T>.Error`
  string, which is human-readable by construction.

#### `GET /worlds/{job_id}/map-document` — response (`MapDocument`)

The shape the client consumes as "the map". Per ADR 0004 §2 this is *the* contract
and lives versioned in `MapGen.Contracts`. Its body is the AMPB vocabulary observed
in `storage/app/maps/*.json`, verbatim, plus the provenance block ADR 0004 §4
requires:

```json
{
  "version": 2,
  "job_id": "43860dcf-6469-42a7-9843-4e33abeacfac",
  "seed": 1234567890,
  "generator_version": "0.1.0-prototype",

  "slug": "default_forest",
  "name": "Default Forest",
  "description": "Generated by MapGen job 43860dcf.",
  "thumbnail_color": "#3a5a2a",

  "human_town_hall": { "row": 14, "col": 1 },
  "human_workers":   [ { "row": 17, "col": 6 } ],
  "orc_buildings":   [ { "type": "town_hall", "row": 5, "col": 55, "tile_size": 4 } ],
  "mines":           [ { "name": "Mine #1", "row": 41, "col": 6, "tile_size": 4 } ],
  "trees":           [ { "row": 0, "col": 0 } ],
  "stones":          [ { "row": 0, "col": 0 } ],
  "roads":           [ { "row": 0, "col": 0 } ]
}
```

Rules that are not negotiable in this slice:

- **`row`/`col`, not `x`/`y`.** AMPB's documents are row/col throughout. The
  pipeline's internal artifacts are x/y. The conversion happens server-side, in the
  export; the client never sees x/y in a MapDocument.
- **Positions are on a fixed 64×64 tile grid** (ADR 0004). ADR 0004's "resolution
  mapping" open question — 64×64 cells expand to 128×128 tiles, but AMPB wants
  64×64 — is **not resolved by this slice**. For the prototype, `MapGen.Api`
  generates at 64×64 cells and the export halves; the client must not assume the
  document grid equals the request's cell dimensions. It reads the grid size from
  the preview (below), never infers it.
- **No passability array.** ADR 0004 §"Passability" keeps it out of v1 so v1 needs
  zero AMPB changes. The client does not expect one.
- `human_workers`, `orc_buildings`, `mines`, `trees`, `stones`, `roads` are always
  **present and possibly empty** — never omitted, never `null`. (`default_forest.json`
  ships `"human_workers": []`; `goldshire.json` omits `mines` entirely. The contract
  picks the strict reading so the client needs no null-coalescing.)
- **`trees` is TreePlanter's canopy**, read from the job's `.worldpayload` and halved
  onto the 64×64 grid (distinct after collapse). It is not the `wood` resource clusters
  Playable marks as harvest sites near each start — that brief mistake exported a map
  with as many trees as wood piles.
- `version` is an integer that increments on any shape change (`AGENTS.md`: no
  silent shape changes). The client asserts `version === 2` and refuses anything else
  loudly rather than parsing leniently.

#### `GET /worlds/{job_id}/preview` — response (`MapPreview`)

```json
{
  "version": 2,
  "job_id": "43860dcf-6469-42a7-9843-4e33abeacfac",
  "width": 128,
  "height": 128,
  "terrain_palette": ["deep_water", "water", "dirt", "grass", "rock", "mountain"],
  "terrain": [3, 3, 2, 0, "… width*height row-major palette indices …"],
  "trees":             [ { "x": 43, "y": 0 } ],
  "start_zones":       [ { "id": "start_1", "x": 43, "y": 80 } ],
  "resource_clusters": [ { "id": "start_1_wood", "type": "wood", "x": 49, "y": 84, "start_id": "start_1" } ]
}
```

- `terrain` is row-major, length `width * height`, indices into `terrain_palette` —
  the same row-major convention `TerrainGrid` already uses (`index = y*width + x`)
  and the same terrain vocabulary `.worldpayload` already emits. Palette indices
  rather than strings keeps a 128×128 preview at ~16 KB of JSON instead of ~100 KB.
- `trees` is the same canopy the map document carries, at tile resolution and before
  the halving — the renderer paints it over the terrain, beneath the markers. It is a
  position list rather than a row-major mask alongside `terrain`: the replayed jobs
  plant 745–1551 of 16 384 tiles, which leaves the whole response around 45 KB. A
  canopy over roughly a third of the grid is where the mask starts paying.
- `start_zones` and `resource_clusters` mirror `.playable.json` verbatim minus the
  fields the renderer has no use for (`slope`, `settlement_labels`).
- Coordinates here are **tile x/y**, matching `.playable.json`. This is the one place
  the client sees x/y, and it is consistent within this document.

### New DTOs and why

| DTO | Reuses | Why it is new |
|---|---|---|
| `MapDocument` | AMPB `storage/app/maps/*.json` vocabulary | Mandated by ADR 0004 §2. New as C#, not new as vocabulary. |
| `GenerateWorldRequest` | `input.job.json` field names | Adds `seed`/`name`; the golden-job spec has neither, and ADR 0004 §4 requires the seed be an explicit input. |
| `JobAccepted`, `JobStatus` | — | Genuinely new. Nothing in the file-driven legacy pipeline models job state over HTTP; the outbox *is* the status today. Async request/response cannot be expressed without them. |
| `MapPreview` | `.worldpayload` terrain vocabulary + `.playable.json` | **Genuinely new, and load-bearing.** A MapDocument is entity *placements* — town hall, mines, trees. It carries no terrain grid at all, so `capybara_2d_engine` cannot render a map from one. Extending MapDocument with terrain would break ADR 0004's "v1 requires zero AMPB changes" rule, so the preview is a separate, prototype-scoped resource that Phase 2 may keep or drop without touching the AMPB contract. |
| `TileRegionResponse`, `AdjacencyMaskResponse` | `MapGen.Cli`'s existing JSON output, field for field | Not new shapes — the CLI already prints exactly these. They exist only because a `Result<TileRegion>` is not itself serialisable at a wire boundary. |

`ResolveTileRegionCommand` and `ComputeAdjacencyMaskCommand` are **reused as-is** as
the request bodies for the two tile endpoints. They are already primitives-only
records at the boundary (parse-don't-validate happens inside the handler), so they
model-bind directly. No request DTO is invented for them.

#### Tile endpoint shapes

```
POST /tiles/expand-cell
  req  { "cell_x": 3, "cell_y": 4, "map_width_in_cells": 10, "map_height_in_cells": 10 }
  res  { "cell": { "x": 3, "y": 4 },
         "tiles": [ {"x":6,"y":8}, {"x":7,"y":8}, {"x":6,"y":9}, {"x":7,"y":9} ] }

POST /tiles/adjacency-mask
  req  { "cell_x": 1, "cell_y": 1, "grid_width": 3, "grid_height": 3,
         "terrain": [1,1,1,1,1,1,1,1,1] }
  res  { "cell": { "x": 1, "y": 1 }, "mask": 15,
         "north": true, "east": true, "south": true, "west": true }
```

`tiles` is ordered **TL, TR, BL, BR** — the contractual order `TileRegion` documents
and `CellToTile.dfy` proves. The client must not re-sort it. `mask` is the raw 0–15
byte; the four booleans are derived (N=1, E=2, S=4, W=8) and sent for readability,
not as independent truth.

### Errors

Every non-2xx response is RFC 7807 `application/problem+json`:

```json
{
  "type": "https://mapgen.local/problems/invalid-request",
  "title": "Invalid request",
  "status": 400,
  "detail": "Cell (12,3) is outside the cell map: the cell coordinate is outside the cell map dimensions 10×10.",
  "instance": "/api/v1/tiles/expand-cell"
}
```

- `Result<T>.Fail(error)` maps to `400` with `Error` as `detail`. Handler failures in
  this codebase are validation failures by construction — `ResolveTileRegionHandler`
  and `ComputeAdjacencyMaskHandler` catch `ArgumentException` /
  `ArgumentOutOfRangeException` and return `Fail`, so a `Result` failure is never a
  server fault.
- Unknown `job_id` → `404`. Collect before `succeeded` → `409`. Unhandled exception →
  `500` with a generic `detail` and no stack trace.
- The client maps `detail` straight to the UI. Error strings are already
  human-readable (see the domain messages above); the client adds no second
  vocabulary of its own.

### Transport, versioning, and access

- **Base URL** is a client build-time env var (`VITE_MAPGEN_API_URL`), defaulting to
  `http://localhost:5187/api/v1`.
- **`MapGen.Api` binds to loopback only** and is never exposed (ADR 0004; slice
  constraint). CORS allows exactly the Vite dev origin. In Phase 2 the Laravel BFF
  becomes the only caller and holds the internal service token; the prototype client
  sends no token, which is safe *only* because the API is loopback-bound.
- **Versioning is in the path** (`/api/v1`) *and* in each document (`version: 2`).
  Path version covers endpoint shape; document version covers payload shape; they
  move independently.
- **The TypeScript types are hand-written in Phase 3a**, mirroring this section, and
  live in one FSD `shared/api` module. ADR 0006's open question — generate the TS
  type from `MapGen.Contracts` or hand-maintain it — stays open; this slice is too
  small to justify a codegen step, and concentrating the types in one module keeps
  the later swap cheap. A Phase 2 endpoint test asserts the JSON matches this
  section, so the hand-written mirror has a server-side guard.
- **OpenAPI**: `MapGen.Api` serves a Swagger document in Development only. It
  describes this contract; it does not define it — this section does.

### What backs generation in this slice

Stated plainly so no later phase is surprised: **`MapGen.Application` contains no
generation handler.** Its entire surface today is the two tile-resolution commands.
The world endpoints above are therefore specified in full but, in Phase 2, backed by
an application-layer job orchestrator that **replays the three golden-job fixtures**
(`tests/fixtures/golden/`) as if they were freshly generated — reading them,
narrating stages, and projecting them into `MapDocument` / `MapPreview`.

This is a legitimate reading of the slice's own rule that it "adds no domain
behaviour": the orchestrator is transport-and-projection, it reproduces no domain
arithmetic, and it touches no fixture (read-only). It also means the client is
developed against real pipeline output rather than invented data. When the .NET
generation stages exist, only what sits behind the endpoints changes; this contract
does not.

If Phase 2 finds it cannot serve these endpoints without adding domain behaviour,
that is the escalation the [Testing obligation](#testing-obligation) section
already calls for — stop, do not widen the slice.

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
