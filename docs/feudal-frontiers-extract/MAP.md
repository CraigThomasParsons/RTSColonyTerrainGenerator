# Extract Map — RTSColonyTerrainGenerator → `ElasticGun/feudal-frontiers` `apps/mapgen`

Inventory for Gitea #98, taken from `main` at `49d4248` (2026-10-06). Read
[`README.md`](README.md) first for the ground rules and the recorded decisions (D1–D5).

Legend for the **Action** column:

- **Move**: goes to `apps/mapgen/<same relative path>` unless a different target is given.
- **Move (rework)**: moves, but monorepo-specific content needs editing after the import.
- **Defer**: belongs with mapgen eventually, but is not part of the first extract. It
  waits for its own ticket.
- **Exclude**: stays in this donor repository. It is not mapgen-core, or it serves a
  different target.

The core rule: `apps/mapgen/` mirrors the donor root. Lanes, the `justfile`,
`tools/mapgenctl`, the BDD `legacy` profile, and the compatibility tests all resolve paths
from the repository root. Keeping the relative layout means none of them change in the
move (README ground rule 2).

---

## 1. Docs spine (move verbatim)

| Donor path | Target | Action | Notes |
|---|---|---|---|
| `mapgen-spec-driven-planning/` (Bible + 00–12 + `AGENTS.md`) | `apps/mapgen/mapgen-spec-driven-planning/` | **Move** | The authoritative migration plan. Keep the directory name: `AGENTS.md`, ADRs, and spec packs link to it by path. Placement guide `12-…` describes an older in-repo layout; do not re-apply it during the extract. |
| `AGENTS.md` | `apps/mapgen/AGENTS.md` | **Move (rework)** | Coding, Dafny, and specification-protection rules carry over unchanged. Rewrite the *Issue Lifecycle (Gitea)* section and the forge URL/lock-file references for the monorepo (D4). |
| `CONTEXT.md` | `apps/mapgen/CONTEXT.md` | **Move** | The ubiquitous language. AGENTS.md points to it. |
| `docs/adr/0001-specification-driven-mapgen.md`, `0002-dafny-as-verified-model.md`, `0003-cucumber-js-bdd-runner.md`, `0004-ampb-integration-boundary.md`, `0005-mediator-in-application-layer.md`, `README.md` | `apps/mapgen/docs/adr/` | **Move** | 0004 defines the HTTP seam and MapDocument contract that Feudal Frontiers consumes. Keep it with mapgen. |
| `docs/adr/0001-pixellab-presentation-only.md` | `apps/mapgen/docs/adr/` | **Move** | Keep it even though PixelLab code is deferred. It is the rule that stops presentation output from ever feeding gameplay. |
| `docs/adr/upstream/` | `apps/mapgen/docs/adr/upstream/` | **Move** | Vendored verbatim from The-Pulse with a provenance line. See §5.4 for the licence caveat. |
| `docs/adr/0006-gamestart-react-fsd-island.md` | — | **Defer** (D5) | Mostly about the AMPB side. Keep it in the donor as historical reference and leave a historical-context pointer in `apps/mapgen/docs/adr/README.md`. Follow the current Feudal Frontiers game plan. |
| `docs/specs/` (`01-cell-to-tile`, `02-adjacency-mask`, `spec-driven-development`, `templates`) | `apps/mapgen/docs/specs/` | **Move** | Spec Packs, part of the dual-reference loop. |
| `docs/baseline/` | `apps/mapgen/docs/baseline/` | **Move** | Phase 0 deliverables: stage inventory, artifact formats, pipeline graph. |
| `docs/Stage_Contract.md`, `docs/AI_Adding_A_Stage.md`, `docs/TheTYSMethod.md`, `docs/WeatherAnalysesSpec.md`, `docs/environment.md` | `apps/mapgen/docs/` | **Move** | Stage authoring conventions and the environment setup. |
| `docs/plans/stage-delivery-manifest.md` | `apps/mapgen/docs/plans/` | **Move** | |
| `docs/plans/map-gui-prototype.md` | `apps/mapgen/docs/plans/` | **Move** | **Required even though the GUI is deferred.** `src/MapGen.Api/README.md` names its *Wire Contract* section as the API contract. |
| `docs/style/` | `apps/mapgen/docs/style/` *or* the monorepo-level style docs | **Move** | AGENTS.md cites `docs/style/javascript_node_style.md`. If the monorepo already has a style guide, merge them and update that link. |
| `docs/go_style.md`, `docs/php_style.md`, `docs/python.md` | — | **Exclude** | Older duplicates of `docs/style/*`. |
| `docs/AncientCivilization.md` | — | **Defer** | Goes with the AncientCivilization stage (§4). |
| `docs/plans/pixellab-*.md` | — | **Defer** | Goes with the PixelLab lane (§4). |
| `docs/reviews/` | — | **Exclude** | Historical review receipts for donor issue #58. They stay in the donor archive. |
| `docs/php_atom_dark.json`, `docs/SimCity.code-workspace` | — | **Exclude** | Editor settings. |
| `MapGenerator/stages.md` | `apps/mapgen/MapGenerator/stages.md` | **Move** | The quick-reference for stages. |

## 2. Mapgen-core runtime (move together)

These are the pieces the dual-reference loop needs: the verified C# side, the specs, the
acceptance lane, the fixtures, and the legacy stages the `legacy` profile runs. They have to
land in the same import, or `npm run bdd:legacy` and the compatibility tests break.

### 2.1 Verified C# solution, specs, acceptance, fixtures

| Donor path | Target | Action | Notes |
|---|---|---|---|
| `src/MapGen.Domain/` | `apps/mapgen/src/MapGen.Domain/` | **Move** | Tile Resolution domain (cell-to-tile, adjacency mask). |
| `src/MapGen.Application/` | `apps/mapgen/src/MapGen.Application/` | **Move** | CQRS handlers (Mediator, ADR 0005), including `WorldGeneration/`. |
| `src/MapGen.Contracts/` | `apps/mapgen/src/MapGen.Contracts/` | **Move** | Home of the versioned MapDocument contract (ADR 0004 §2). This is the public surface Feudal Frontiers depends on. |
| `src/MapGen.Cli/` | `apps/mapgen/src/MapGen.Cli/` | **Move** | |
| `src/MapGen.Api/` (excluding `PixelLab/` and `Endpoints/PixelLabEndpoints.cs`) | `apps/mapgen/src/MapGen.Api/` | **Move (rework)** | The HTTP seam from ADR 0004. `Replay/` moves with it. In `Program.cs`, remove the PixelLab namespace import, options/service/executor registrations and `MapPixelLabEndpoints()` call before building. Retain world/tile routing and shared infrastructure. |
| `src/MapGen.Api/PixelLab/`, `src/MapGen.Api/Endpoints/PixelLabEndpoints.cs` | — | **Defer** | Presentation-only implementation and endpoints (§4). Remove their startup references in the import commit; disabling registration alone cannot remove compile-time dependencies. |
| `tests/MapGen.Domain.Tests/`, `MapGen.Application.Tests/`, `MapGen.ArchitectureTests/`, `MapGen.CompatibilityTests/` | `apps/mapgen/tests/…` | **Move** | |
| `tests/MapGen.Api.Tests/` (excluding `PixelLabEndpointTests.cs` and `Support/FakePixelLabProcessExecutor.cs`) | `apps/mapgen/tests/MapGen.Api.Tests/` | **Move (rework)** | Keep shared `Support/MapGenApiFactory.cs`, but remove its PixelLab namespace import, `PixelLabExecutor` property and executor replacement block before building. Preserve its clock, options and Golden Job substitutions. |
| `tests/MapGen.Api.Tests/PixelLabEndpointTests.cs`, `tests/MapGen.Api.Tests/Support/FakePixelLabProcessExecutor.cs` | — | **Defer** | Follow the deferred provider implementation. |
| `tests/bdd/` (`features/`, `steps/`, `support/`, `net-ready.tags`) | `apps/mapgen/tests/bdd/` | **Move** | The cucumber-js lane (ADR 0003). The promotion ledger moves unchanged. |
| `tests/fixtures/golden/` | `apps/mapgen/tests/fixtures/golden/` | **Move (byte-for-byte)** | About 15 MB, mostly three `.worldpayload` files. Never regenerate them in the move. If the monorepo uses Git LFS, decide that before import, because LFS rewrites change blob identity but not content. |
| `specs/` (`tiling/`, `logging/`, `dafny-ready.tags`, `README.md`) | `apps/mapgen/specs/` | **Move** | Dafny Verified Model and the formal promotion ledger. |
| `MapGen.slnx` | `apps/mapgen/MapGen.slnx` | **Move** | Can later join a monorepo-level solution. Keep the per-app solution as well. |
| `justfile` | `apps/mapgen/justfile` | **Move** | The gate surface (`quality`, `verify`, `bdd-*`, `run-legacy`). A monorepo root `justfile` can delegate to it with `just -f apps/mapgen/justfile`. |
| `package.json`, `package-lock.json`, `cucumber.mjs` | `apps/mapgen/` | **Move** | The BDD runner's dependencies. If the monorepo uses npm/pnpm workspaces, register `apps/mapgen` as a workspace instead of hoisting. |
| `.gitignore` | merge into `apps/mapgen/.gitignore` | **Move (rework)** | Lane `inbox/`/`outbox/` and build-output ignores must keep applying under the new prefix. |
| `README.md` | `apps/mapgen/README.md` | **Move (rework)** | Rewrite the intro for the monorepo context. |

### 2.2 Legacy Pipeline stages (the baseline)

`tools/mapgenctl` runs `heightmap → tiler → weather → treeplanter` as the mandatory
chain (`tools/mapgenctl/cli.py`, `PIPELINE_STAGES`). ADR 0004 says Feudal Frontiers/AMPB
needs everything through **Playable**. So the baseline that moves is the short path to
Playable.

| Donor path | Language | Target | Action | Notes |
|---|---|---|---|---|
| `MapGenerator/Heightmap/` | Rust | `apps/mapgen/MapGenerator/Heightmap/` | **Move** | Entry stage. |
| `MapGenerator/WeatherAnalyses/` | Rust | `apps/mapgen/MapGenerator/WeatherAnalyses/` | **Move** | Has a committed ELF `bin/weather-engine` (see §6). |
| `MapGenerator/Tiler/` | C# | `apps/mapgen/MapGenerator/Tiler/` | **Move** | The legacy reference for Phases 2–3. |
| `MapGenerator/TreePlanter/` | PHP | `apps/mapgen/MapGenerator/TreePlanter/` | **Move** | Emits the first World Payload. Ships a committed `vendor/composer` autoloader and `bin/composer` (MIT, see §5.4). |
| `MapGenerator/WorldFeatures/` | Kotlin | `apps/mapgen/MapGenerator/WorldFeatures/` | **Move** | Upstream of Playable. |
| `MapGenerator/PathFinder/` | Kotlin | `apps/mapgen/MapGenerator/PathFinder/` | **Move** | Phase 8 Traversal context. |
| `MapGenerator/Playable/` | Python | `apps/mapgen/MapGenerator/Playable/` | **Move** | Produces `.playable.json`, the input to the planned `AgileMedievalExport` stage. |
| `MapGenerator/bin/trace_pipeline*.sh` | Bash | `apps/mapgen/MapGenerator/bin/` | **Move** | Pipeline tracing. |
| `MapGenerator/*/systemd/`, `*/install.sh` | — | with their stage | **Move (rework)** | Several units hard-code `/home/craig…` paths (Heightmap queue, TreePlanter path/service). They need re-pathing before anyone installs them from the monorepo. |

**Fresh-clone gotchas.** Both of these were seen on a clean worktree of the donor on
2026-10-06, and both will reappear in the monorepo:

- `tests/bdd/support/legacy_tiler_probe.js` runs `MapGenerator/Tiler/bin/published/Tiler`,
  which is an **untracked build output**. Until `MapGenerator/Tiler/build.sh` has run, every
  `legacy`-profile Tiler scenario fails with `ENOENT`.
- The smoke scenario *"every stage provides an executable bin lane"* walks every directory
  under `MapGenerator/`. `InfrastructureBuilder/` and `WorldTilemap/` have no tracked `bin/`,
  because git does not track empty directories, so the scenario fails on a fresh clone.
  Deferring those two stages (§4) removes the problem. If they move anyway, give them a
  tracked `bin/.gitkeep`.

### 2.3 Tooling

| Donor path | Target | Action | Notes |
|---|---|---|---|
| `tools/mapgenctl/` | `apps/mapgen/tools/mapgenctl/` | **Move** | `python -m tools.mapgenctl run`. It resolves the MapGenerator root relative to itself, so keep the layout. |
| `tools/artifact_hash/` | `apps/mapgen/tools/artifact_hash/` | **Move** | A Phase 0 deliverable. |
| `tools/README.md`, `tools/USAGE.md`, `tools/create_module.sh`, `tools/start.sh`, `tools/cleaner` | `apps/mapgen/tools/` | **Move** | |
| `tools/ai_test/`, `tools/pipeline_ai_test/` | — | **Defer** | These validate WorldPreview/WorldSnapshot output, which is deferred (§4). |
| `scripts/tools/capture_treeplanter_worldpayload.php`, `scripts/tools/stage_manifest.py` | `apps/mapgen/scripts/tools/` | **Move** | Fixture capture and stage-delivery manifest tooling. |
| `scripts/tools/tests/test_stage_manifest.py` | `apps/mapgen/scripts/tools/tests/test_stage_manifest.py` | **Move** | Core stage-manifest regression coverage. Required by the retained `justfile` quality → test-tools gate. |
| `scripts/tools/*gitea*.py`, `start_/end_/park_gitea_issue.py`, `parking_policy.py`, `check_gitea_state.py`, `create_sprint_issue.py`, `mark_issues_complete.py`, `bootstrap_gitea_repo.py`, `sync_gitea_to_github.sh`, `night_shift*.sh`, `launch_agent_phase.sh`, `prompts/` | — | **Exclude** (D4) | Forge and agent-orchestration tooling hard-coded to `craigpars/RTSColonyTerrainGenerator`. Use Feudal Frontiers’ existing repository workflow (D4). These are not mapgen behaviour; the stage-manifest tests in the preceding row are core tooling and do move. |
| `Logger/` (`logstreamer.sh`, systemd) | `apps/mapgen/Logger/` | **Move** | Aggregates per-stage logs. AGENTS.md requires logs correlated by job and attempt. |

## 3. AMPB-coupled material

There is no AMPB *code* in this repository (ADR 0004: "AMPB stays as it is"). The coupling
is only the contract and docs that describe the seam:

| Donor path | Action | Notes |
|---|---|---|
| `docs/adr/0004-ampb-integration-boundary.md` | **Move** | Defines the seam: `POST /worlds`, `GET /worlds/{id}`, `GET /worlds/{id}/map-document`. Mapgen owns it. |
| `src/MapGen.Contracts/Worlds/`, `src/MapGen.Application/WorldGeneration/` | **Move** | The MapDocument contract and its handlers are mapgen's side of the seam. |
| `docs/adr/0006-gamestart-react-fsd-island.md` | **Historical reference** (D5) | Keep the older AMPB React/Laravel BFF design in the donor. Link it as historical context; the current Feudal Frontiers game plan governs implementation. |
| Planned `AgileMedievalExport` stage | — | Not built yet. When it is, it lives in `apps/mapgen` and emits the 64×64 MapDocument (the final acceptance target in AGENTS.md). |

Inside the monorepo, the integration should stay **HTTP + versioned JSON schema**, as ADR
0004 decided. Do not take the shortcut of a project reference from the game app into
`MapGen.*` assemblies. Besides undoing ADR 0004, a direct link affects the licence analysis
in §5.

## 4. Defer list (mapgen-adjacent, own ticket later)

| Donor path | Why deferred |
|---|---|
| `MapGenerator/PixelLabPresentation/`, `src/MapGen.Api/PixelLab/`, `src/MapGen.Api/Endpoints/PixelLabEndpoints.cs`, `tests/MapGen.Api.Tests/PixelLabEndpointTests.cs`, `tests/MapGen.Api.Tests/Support/FakePixelLabProcessExecutor.cs`, `docs/plans/pixellab-*.md` | Presentation-only (ADR 0001-pixellab) and the only path to a **paid provider**. Defer it so the first extract cannot make network or spending calls. |
| `MapGenerator/MapTexture/` | Optional presentation lane, offline-only. It is safe but not core (D3). Its README cites Map Mosaic (GPL-3.0) as *prior art only*; that claim needs a recheck before moving (§5.4). |
| `clients/mapgen-gui/` + `third_party/capybara_2d_engine/` | The Map Studio prototype GUI. It is presentation, and it may become a monorepo frontend app rather than part of `apps/mapgen` (D3). Capybara is MIT with a `PROVENANCE.md`, so keep both files when it moves. |
| `MapGenerator/WorldPreview/`, `MapGenerator/WorldSnapshot/` | Human inspection branches, not needed for the MapDocument (stages.md notes). They have committed ELF binaries (§6). |
| `MapGenerator/AncientCivilization/` | Wired, but emits largely placeholder content (`docs/baseline/stage-inventory.md`). Has committed ELF binaries. |
| `MapGenerator/InfrastructureBuilder/`, `MapGenerator/WorldTilemap/` | Planned only (plan docs, no engine). |
| `HeightmapApi/` | A PHP enqueue API that the ADR 0004 seam (`MapGen.Api`) is replacing. Bring it only if something still calls it. |
| `docker-compose.yml`, `DOCKER_COMPOSE_*.md`, `.env.example` | Composes `heightmap-api`, `mapgen-web`, `web-dashboard`, and `mapgen`. Re-derive this for the monorepo's deployment (podman quadlets) rather than copying it. |
| `mapgen-web/` | A Go pipeline dashboard with committed 9 MB server binaries. It is an ops UI, not mapgen behaviour. |

## 5. Licence and provenance — accepted target decision, import gate pending

**This ticket changes no licence file and performs no import.** D1 follows Feudal
Frontiers [ADR 0002 — copyright and donor provenance](http://192.168.2.48:3000/ElasticGun/feudal-frontiers/src/branch/develop/docs/adr/0002-copyright-and-donor-provenance.md),
accepted 2026-09-25 and reaffirmed by Craig on 2026-10-06. The target distribution
choice is all rights reserved for Craig’s original code; third-party terms remain applicable.

### 5.1 Donor distribution and existing rights

The donor root `LICENSE` contains GNU GPL version 2. Preserve that distribution history
in provenance records. The target decision does not revoke rights already granted for
previous GPL copies, establish ownership of third-party content, or automatically
relicense the donor. Confirm the applicable terms for each selected component before
import; do not infer that an entire tree can use the target terms from its location alone.

### 5.2 Required extraction manifest (D2)

Before each import, record:

- donor repository URL and immutable revision;
- selected paths, original notices and applicable distribution terms;
- ownership/provenance evidence for original contributions;
- third-party code, dependencies and assets, their terms and notices to retain;
- unresolved items and the affected paths withheld from import.

Unresolved provenance blocks the affected import, not the entire target scaffold. Retain
all required third-party notices. The import ticket must explicitly record the approved
licence handling; this inventory is not approval to copy under different terms.

### 5.3 Contributor verification

The original inventory reported multiple owner identities and five bot-authored commits.
Treat that as a lead for the selected revision’s rights audit, not proof of ownership.
Inspect contributions and provenance evidence, including agent-assisted contributions,
rather than treating author names or bot attribution as a licence grant. Any unresolved
rights question belongs in the extraction manifest before the affected paths move.

### 5.4 Third-party and vendored material with its own terms

| Path | Licence | Extract note |
|---|---|---|
| `third_party/capybara_2d_engine/` | MIT (`LICENSE` + `PROVENANCE.md`) | Deferred with the GUI. Keep both files verbatim when it moves. |
| `third_party/StormLib/` | MIT | Only referenced by `build_extract.md` (the Stargus build). **Excluded** with StargusExport. |
| `MapGenerator/TreePlanter/vendor/composer/`, `MapGenerator/TreePlanter/bin/composer` | MIT (Composer) | Moves with TreePlanter, and `vendor/composer/LICENSE` stays. Consider dropping the committed `vendor/` and `bin/composer` and running `composer install` instead. That is a separate change. |
| `docs/adr/upstream/` | **Unstated.** Vendored from The-Pulse (`ThePulse-Golf/The-Pulse`). | Verify The-Pulse’s licence or ownership evidence before importing these paths; retain provenance and any applicable notices. |
| `MapGenerator/MapTexture/` | GPL-2 (donor) | Its README says Map Mosaic (**GPL-3.0**) was "inspected only as prior art" and no code was used. Verify the prior-art claim and any applicable third-party terms before MapTexture moves. The target ADR does not override third-party terms. |
| External runtimes: Stratagus/Stargus (StargusExport, CartridgeManufacturer `wcar_run_stratagus`), OpenTTD (TransportTycoonDeluxe) | GPL-2 (upstream projects) | They are invoked as separate processes and not vendored here, so they are not a combined work. All three stages are **excluded** (§7) regardless. |

## 6. Build outputs committed to the donor

These are tracked binaries. GPL-2 §3 ties any distributed object code to its source.
Rebuilding from source in the monorepo is cleaner than carrying blobs.

| Path | Size | Recommendation |
|---|---|---|
| `MapGenerator/WeatherAnalyses/bin/weather-engine` | ~1.1 MB ELF | The legacy lane invokes it. Build it from `MapGenerator/WeatherAnalyses/src` in the import (add a `just` recipe), or carry it with a note recording the source commit. |
| `MapGenerator/AncientCivilization/ancientcivilization-engine`, `…/bin/ancientcivilization-engine/ancientcivilization-engine` | ~0.6 MB ×2 | Deferred with the stage. |
| `MapGenerator/WorldPreview/worldpreview-engine`, `…/bin/worldpreview-engine/worldpreview-engine` | ~1.9 MB ×2 | Deferred with the stage. |
| `mapgen-web/server`, `mapgen-web/bin/server` | ~9 MB ×2 | Deferred with `mapgen-web`. |
| `MapGenerator/TreePlanter/bin/composer` | ~3.2 MB phar | See §5.4. |

## 7. Exclude list (stays in the donor)

| Donor path | Reason |
|---|---|
| `MapGenerator/StargusExport/`, `MapGenerator/run_stargus_export.sh`, `build_extract.md`, `third_party/StormLib/` | StarCraft CHK/SCM target. ADR 0004 says it serves "other targets", and it is coupled to GPL Stratagus/Stargus at runtime. |
| `MapGenerator/CartridgeManufacturer/` | WCAR/Stratagus target. Same reasoning as StargusExport. |
| `MapGenerator/TransportTycoonDeluxe/` | OpenTTD scaffold, placeholder output. |
| `MapGenerator/CivicOverreach/`, `MapGenerator/SimulateCity/` | Experimental heuristics that are not on the gameplay chain. SimulateCity is a near-duplicate of CivicOverreach. |
| `MapGenerator/PostalServiceProposal.md`, `MapGenerator/RTSColonyTerrainGenerator.code-workspace` | Proposal notes and editor workspace. |
| `MapGenerator/bin/install_leftoff_autosave.sh`, `MapGenerator/bin/save_leftoff.sh`, `MapGenerator/systemd/leftoff-autosave.*` | Personal "where I left off" autosave tooling. |
| `Web/` | A generic LCARS pipeline dashboard that also drives non-mapgen pipelines (`pipelines/bandcamp.yaml`). |
| `TempDeletedPossibleFuture/` | Parked TreePlanter code. Not used. |
| `ImplementationPlanAndExecution.md`, `Thoughts.md`, `todo.md`, `where_I_left_off.md`, `TYS_FINAL_REPORT.md`, `PATHFINDER_TYS_COMPLETE.md`, `runtest.sh` | Donor working notes and old reports. History stays in the archive. |
| `.beads/` | Donor-local issue tracking state. |
| `docs/reviews/`, `docs/go_style.md`, `docs/php_style.md`, `docs/python.md`, `docs/php_atom_dark.json`, `docs/SimCity.code-workspace` | See §1. |
| `scripts/tools/` forge and agent tooling (not the moved capture/manifest tools or `tests/test_stage_manifest.py`) | See §2.3 (D4). |
| `logs/` (untracked) | Runtime output. |

## 8. CQRS strangler steps — pointer, not a rewrite

The migration plan is
[`mapgen-spec-driven-planning/04-migration-roadmap.md`](../../mapgen-spec-driven-planning/04-migration-roadmap.md)
(with the Bible and `02-target-architecture.md`). It moves with the code unchanged. In
short, the extract changes *where* this work happens, not *what* it is:

| Roadmap phase | Milestone | Where it stands at extract time |
|---|---|---|
| 0 Baseline and safety net | M1 | Done in the donor: `docs/baseline/`, golden jobs, `tools/artifact_hash`, root `justfile`. All of it moves. |
| 1 Specification skeleton | M2 | Done: `src/MapGen.*`, Spec Pack templates, cucumber-js dual profiles, Dafny entry point. |
| 2 Cell-to-tile vertical slice | M3 | Slice `01-cell-to-tile`: spec pack, `CellToTile.dfy`, Tile Resolution domain. |
| 3 Tile Resolution context | M4 | In progress: `02-adjacency-mask` landed. The rest of the Tiler rules, plus a legacy adapter and dual-run, remain. |
| 4 Pipeline Lifecycle | M5 | Not started. Explicit job/stage state machine with verified transitions. |
| 5 Heightmap validation boundary | M6 | Not started. Wrap the Rust stage behind a C# reader/validator, keep Rust. |
| 6 Weather Analysis | (M6–M7) | Not started. Structural invariants first. |
| 7 Vegetation contracts | M7 | Not started. PHP TreePlanter stays behind an adapter. |
| 8 Traversal | M8 | Not started. PathFinder specification-first. |
| 9 Operational consolidation | M9 | Partly started: `MapGen.Api` is the seam from ADR 0004. Worker host, manifests, and deployment remain. |

The strangler pattern itself does not change in the monorepo: one Slice at a time, each
behind an adapter, proven green on the `legacy` and `net` BDD profiles plus Dafny before the
slice's tag is promoted. The roadmap's *Rewrite Rule* still applies, so moving into a
monorepo is not, by itself, a reason to rewrite any legacy stage.
