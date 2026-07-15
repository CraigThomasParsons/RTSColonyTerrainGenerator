# 0004 — AgileMedievalPeasantBoard integration boundary

Status: Accepted (proposed 2026-07-13; accepted on merge of PR #5, 2026-07-14)

## Context

The programme's end goal (ADR [0001](0001-specification-driven-mapgen.md), `AGENTS.md`
mission) is to emit AgileMedievalPeasantBoard's map-document payload from the verified
pipeline. This ADR fixes *how* the two systems meet, so every slice knows what it is
building toward. It changes nothing in AMPB.

Facts that constrain the design:

- **AMPB stays as it is.** Laravel 13 + PixiJS, server-authoritative simulation, no .NET
  runtime. The verified C# MapGen therefore runs as a separate process; a linked-library
  integration is impossible and a shared-filesystem integration couples two independently
  deployed systems (both live as podman quadlets on the NAS).
- **AMPB already has the consuming machinery.** Map documents are JSON
  (`storage/app/maps/*.json` → `map_documents` table →
  `GameController::applyMapTemplate()` → `GameSession::startFreshFromMapDefinition()`),
  and Laravel Reverb/Echo provides the push channel to the browser. AMPB's
  `docs/dreams/procedural_generation/world-generator.md` already names this repository as
  the intended generator.
- **The observed map-document vocabulary** (from `storage/app/maps/`, richest in
  `default_forest.json` / `black-morass.json`): `slug`, `name`, `description`,
  `thumbnail_color`, `human_town_hall {row,col}`, `orc_buildings[] {type,row,col,tile_size}`,
  `human_workers[] {row,col}`, `mines[]`, `trees[]`, `stones[]`, `roads[]` — all
  positions on a fixed **64×64 grid** of 16px tiles. Passability is *not* part of the
  document: it is a hardcoded 64×64 array in AMPB's `resources/js/editor/impassable.ts`.
- **Generation is not instant.** A pipeline run crosses many stages and languages
  (seconds to minutes), so a blocking "New Game" HTTP call is not viable. The player-facing
  flow must be RimWorld-shaped: request generation, watch progress, then enter the world.
- **AMPB does not need the whole pipeline.** Tiles, terrain, start zones, and resource
  clusters all exist by the WorldFeatures/Playable stages (`.worldpayload` +
  `.playable.json`). StargusExport, CartridgeManufacturer, WorldPreview/Snapshot serve
  other targets.

## Decision

### 1. The seam is a thin HTTP service in front of MapGen

The Phase 9 worker host (`MapGen.Api`) exposes the CQRS boundary as the integration
surface:

```
POST /worlds           { seed, width, height, params }   -> { jobId }
GET  /worlds/{jobId}                                     -> { status, stage, pct }
GET  /worlds/{jobId}/map-document                        -> versioned MapDocument JSON
```

Asynchronous request/response: submit → job id → collect when ready. No shared volume
and no knowledge of MapGen's lane layout crosses the deploy boundary. AMPB drives this
from a queued Laravel job and narrates progress to the player over its own Reverb/Echo
channels; that AMPB-side flow is future AMPB work and is deliberately out of scope here.

A filesystem/CLI spike (writing a job spec into the pipeline inbox, watching the outbox)
is acceptable for local development but is **not** the contract.

### 2. The MapDocument schema is *the* contract, versioned in `MapGen.Contracts`

A `MapDocument` schema conforming to the observed AMPB vocabulary above lives in
`MapGen.Contracts` with an explicit version field. "The pipeline emits a valid MapDocument"
is the programme's final acceptance test — a Gherkin contract like any other slice, run
against both profiles. Schema changes follow the same rules as any artifact schema
(`AGENTS.md`: no silent shape changes; version on change).

### 3. A terminal `AgileMedievalExport` stage produces it, via the short path

The export consumes `.worldpayload` + `.playable.json` (the Playable stage's outputs) and
emits a MapDocument: start zones → `human_town_hall` / opponent placements, resource
clusters → `mines`/`trees`/`stones`, terrain → entity placement and (optionally, see
below) passability. It is a specification-first stage in the roadmap's sense — built
through requirement → BDD → contract → C#, with the golden jobs as its input fixtures.

### 4. Determinism is the provenance story; AMPB still owns the game

MapGen is a pure function: seed + params + generator version → map. The MapDocument
carries `seed`, `generator_version`, and `job_id` so any map is reproducible and
auditable. AMPB persists the concrete document in its own DB regardless (its
authoritative simulation owns runtime state), and MapGen contains no gameplay logic —
it produces data; AMPB plays the game.

## Open questions (deferred to the export slice's Spec Pack)

- **Resolution mapping.** AMPB's grid is 64×64 *tiles*; the pipeline's cell-to-tile
  expansion turns 64×64 cells into 128×128 tiles. Either generate at 32×32 cells or
  downsample in the export stage. Decide with fixtures in hand.
- **Passability.** Today's AMPB document has no impassable grid (it is hardcoded
  client-side). Exporting one is a natural extension AMPB may adopt later — kept out of
  the v1 contract so that v1 requires zero AMPB changes.
- **Push vs poll for progress.** Webhook from `MapGen.Api` versus Laravel polling
  `GET /worlds/{jobId}`. Decide when the worker host is built; the endpoint shape above
  supports either.

## Consequences

- Every upstream slice inherits a concrete target: the final acceptance boundary is the
  same public boundary a real client (AMPB) will call.
- MapGen and AMPB deploy and evolve independently; the only coupling is a versioned JSON
  schema — the same integration grammar AMPB already speaks for hand-authored maps.
- A new service must eventually be hosted (one more quadlet) and the schema needs
  versioning discipline; both are Phase 9 costs the roadmap already carries.
- Until the export slice lands, this ADR is the north star, not a work item: nothing in
  M1–M3 changes because of it, but slice designs should avoid decisions that would
  contradict it (e.g. baking a StarCraft-only assumption into shared contracts).
