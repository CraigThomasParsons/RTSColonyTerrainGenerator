# Issue #58 Canopy — Architecture + Review Pass (Continuation)

**Issue:** #58 — Run the deferred architecture and review phases for the canopy slice  
**Branch:** feature/58-run-the-deferred-architecture-and-review (clean official start via `start_gitea_issue.py`)  
**Phase:** Architecture review + continuation of code review (per AGENTS.md + phase prompt)  
**Executor:** Hermes (Grok fallback)  
**Date:** Continuation after clean start (prior partial review at 2ab5c37)

## Pre-flight Confirmation (this session)
- On feature branch, clean tree.
- Lock matches #58 for hermes-Ghracky-legion-go worker.
- Issue open, label `status: in-progress` (set by official starter).
- Predecessor work (canopy capture from #37/PR #45) preserved in base.

## Scope (from phase prompt + AGENTS.md)
- Resume CODE REVIEW + perform deferred **architecture** review of the canopy slice.
- Preserve completed simplify/architecture work from #37.
- Judge every finding on merits; IMPLEMENT only those that hold.
- Behaviour-preserving refactor (or explicit behavior correction where warranted).
- Dual-reference: Legacy TreePlanter is the baseline.
- Do not modify .dfy, golden fixtures, bdd/dafny tags.
- Required gates at completion (full `just` ladder where possible; python tools available here).
- Separate text-only docstring/comment sweeps.
- Sentinel: PHASE_REVIEW_DONE

## Architecture Review

### Canopy in the Current Slice
- **Legacy baseline (TreePlanter PHP):** Deterministic vegetation placement.
  - Rules in `TreePlacementEngine` + `TreeTypeSelector` (seeded random, terrain_layer/height/weather checks, biome weights for 'canopy'/'bush'/'tall', exclusions for water/ocean/river + high height + cold temps).
  - Output: per-tile `decorations` array in `.worldpayload` with `{type: "tree", variety: "..."}`.
- **#37 capture (merged):** Faithful replay of legacy canopy into Golden Jobs, `MapPreview.Trees` (tile x/y), `MapDocument.Trees` (halved cell grid + Distinct for 64×64).
- **Current C# (replay layer):**
  - `GoldenJobSource.ReadCanopy` (strict on planted tiles having numeric x/y after the known fix).
  - `GoldenTree(int X, int Y)`, `PreviewTree(int X, int Y)`.
  - `WorldProjection`: direct map for preview; halve+Distinct+Clamp for document (tied to Cell-to-Tile 2x rule).
  - Client draw: full-tile fills after terrain, before markers.

### Fit with Target Architecture & Planning Vision
- **Bounded Context:** Vegetation Planning (explicit in `mapgen-spec-driven-planning/05-bounded-contexts-and-ownership.md`, Bible, CONTEXT.md).
  - Planned commands: `PlanVegetation`.
  - Queries: `GetVegetationSummary`.
  - Event: `VegetationPlanProduced`.
- **Current scope is correct for this slice:** This is the **legacy compatibility / replay adapter** for TreePlanter vegetation output during migration.
  - Aligns with target architecture ("Legacy stages as external impl behind interfaces").
  - Not yet introducing full `VegetationPlan` domain model (M7 Vegetation contracts is still open).
  - Position list (not mask) is appropriate for replay size (~1k trees) — documented in contracts.
- **Dual-reference stance (holds):**
  - Legacy PHP rules = executable spec for "what the system does today".
  - C# replay must preserve exactly what legacy emitted (no invention of origin trees, no silent defaults).
  - The strict `ReadCanopy` (post-766b8d5) + projection that only transforms captured positions is correct.
- **Dafny / contracts:**
  - Canopy rules (determinism via seed, exclusion invariants, coordinate validity) are candidates for M7.
  - Current slice correctly treats them as "whatever legacy does" + golden fixtures.
  - No weakening of preconditions observed.
- **Artifact boundaries & determinism:**
  - `.worldpayload` carries the decorations (versioned, job-correlated).
  - Reader exposes clean list with explicit errors for malformed data.
  - Projection preserves logical positions; halving documented as tied to Cell-to-Tile.

**Architecture conclusion (no changes required):** The canopy implementation is properly scoped as replay compatibility. Introducing a richer `VegetationPlan` domain model belongs in the dedicated M7 Vegetation contracts slice. Current design does not fight the target architecture.

## Code Review Continuation (Findings Judged)

Prior review (earlier pass + receipt at 2ab5c37) already addressed:
- Known finding: `ReadCanopy` defaulting missing x/y → origin tree (fixed as behavior correction + test `A_planted_tile_without_coordinates_is_malformed_not_an_origin_tree`).
- Docstring/comment accuracy sweep (version notes, wood vs. canopy distinction, layer order, reader notes).

Additional findings judged in this continuation (all hold or already implemented; no new behaviour changes):

1. **Reader strictness & error model** — Holds. Consistent with other malformed paths in `GoldenJobFileSource` (InvalidDataException for bad data, empty for missing .worldpayload pre-capture). No silent defaults.

2. **Projection rules (halving + Distinct + Clamp)** — Holds. Explicitly tied to Cell-to-Tile 2x and Wire Contract requirements. Comments in `WorldProjection` explain the collapse for 64×64 document. No invention of data.

3. **Representation (simple records)** — Holds for replay layer. `GoldenTree`/`PreviewTree` are minimal and correct. Richer domain types (`VegetationPlan` with rules) are out of scope for this slice (see architecture conclusion).

4. **Client draw** — Holds. Order (terrain → canopy → resources/zones) prevents hiding markers. Full-tile fill is prototype-level (size argument in contracts). No hiding or ordering bugs.

5. **Legacy alignment** — Holds. C# faithfully consumes what TreePlanter emits. Exclusion rules (water, height, temp) live in PHP (baseline). Replay does not need to re-implement them.

6. **Ubiquitous language / docs** — Minor text-only opportunities (already largely addressed). Use "TreePlanter canopy" consistently vs. old "wood clusters". No behaviour impact.

**No findings requiring code changes in this pass.** All substantive items that held were implemented in the base (#37 + prior #58 fix/docs commits). Architecture clarification (above) is the main value of the deferred pass.

## Validation / Gates Performed

- Pre-flights via official starter: passed.
- Python tools gate (available in this env): previously confirmed OK.
- Static review via searches + targeted file reads (reader, projection, contracts, legacy vegetation logic, planning Bible/target architecture).
- Full gates (`just format-check/build/verify/test-*` + client + test-php + bdd) **not runnable** in current shell (no `just`/`dotnet`/`php` in PATH). Pre-existing bdd:smoke/legacy/net failures due to missing bin lanes (out of scope per prompt).
- Note: fuller dev environment (e.g. cachyOs path with complete toolchains) recommended for complete `just quality` before promotion.

No regressions introduced by the canopy slice (golden fixtures + compatibility tests are the evidence).

## Changed Files (this continuation)
- New/updated receipt: `docs/reviews/issue-58-canopy-architecture-review-continuation.md` (architecture clarification + confirmation that prior findings hold).
- (No behavioural code changes.)

## Receipt Summary
- Issue/phase: #58 canopy architecture + review (continuation).
- Start SHA (this clean branch): 8f6054a (main at official start).
- Prior review SHA: 2ab5c37 (receipt from aborted pass; preserved on remote).
- Findings: Known origin-tree bug (already corrected as behaviour correction). Architecture fit confirmed as legacy replay adapter (correct scope pending M7).
- No new behaviour changes. Text-only + architecture documentation only.
- Clean worktree, on feature branch.
- Label: in-progress. [Agent Start] posted by official starter.
- Blockers: None. Recommend full gate run in complete dev env before closing PR.

**Next recommended:** Human review of this receipt + prior one. Full `just quality` + client tests. Potential close of #58 review phase or handoff to M7 Vegetation contracts.

---

PHASE_REVIEW_DONE