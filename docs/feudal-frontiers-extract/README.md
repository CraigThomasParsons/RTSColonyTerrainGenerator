# Feudal Frontiers Extract — Donor Notes (RTSColonyTerrainGenerator → `apps/mapgen`)

Status: **Inventory only** (Gitea #98, 2026-10-06). Nothing has been moved yet.

## Why this exists

The Feudal Frontiers monorepo plan puts terrain generation in `apps/mapgen` inside
`ElasticGun/feudal-frontiers`. That repository now exists. These notes prepare the
extract from this donor repository; approving this inventory does not perform an import.

The scope is narrow on purpose:

- **Inventory.** Decide what moves, what stays here, and what is deferred.
- **No architecture changes.** The target architecture and the migration steps are
  already decided in [`mapgen-spec-driven-planning/`](../../mapgen-spec-driven-planning/00-README.md).
  The extract moves that plan along with the code. It does not replace it.
- **No provider calls.** No PixelLab, AI detailing, or paid-provider runs happened while
  preparing this, and none are needed to carry it out.

## How to read this folder

| File | What it gives you |
|---|---|
| [`MAP.md`](MAP.md) | The path-by-path map: donor path → `apps/mapgen/...`, plus the **exclude** and **defer** lists, the CQRS strangler-step summary, and the **licence (GPL-2) notes** |
| this README | Purpose, ground rules, Craig’s recorded decisions, and the order to carry out the extract |

## Ground rules for the extract

1. **The planning pack stays the docs spine.** `mapgen-spec-driven-planning/` moves
   verbatim. The Bible, `02-target-architecture.md`, `04-migration-roadmap.md`, and
   `12-repository-placement-guide.md` remain the authority. MAP.md only summarises them.
2. **Keep relative paths inside `apps/mapgen`.** Stage lanes (`MapGenerator/<Stage>/inbox|outbox`),
   `tools/mapgenctl`, the `justfile`, the BDD `legacy` profile, and the compatibility tests
   all resolve paths relative to the repository root. If `apps/mapgen/` mirrors the donor
   root, those keep working. The monorepo root takes no part in mapgen's path resolution.
3. **The legacy pipeline is still the baseline.** The `legacy` BDD profile has to stay
   runnable after the move. Move the stages it depends on together with the C# solution.
   Do not ship half of the dual-reference loop.
4. **Golden Job fixtures move byte-for-byte.** `tests/fixtures/golden/` is copied as-is,
   never regenerated, so the compatibility tests and artifact hashes still hold.
5. **History.** Prefer a history-preserving import (`git subtree add --prefix=apps/mapgen`
   or `git filter-repo --to-subdirectory-filter apps/mapgen`) over a flat copy. The GPL-2
   copyright and provenance trail lives in the commit history (see MAP.md §5).
6. **Leave the donor intact.** This repository stays as the archive and as the home of
   everything on the exclude list. Remove nothing here as part of the extract.

## Decisions recorded by Craig (2026-10-06)

D1, D3, D4, and D5 were confirmed in the PR #104 review conversation. D2 is
verification work, not an assertion that provenance has already been checked.
The target decision is recorded in Feudal Frontiers
[ADR 0002 — copyright and donor provenance](http://192.168.2.48:3000/ElasticGun/feudal-frontiers/src/branch/develop/docs/adr/0002-copyright-and-donor-provenance.md),
accepted 2026-09-25. This documentation PR changes no licence file and imports nothing.

| # | Decision | Follow-up / boundary |
|---|---|---|
| D1 | Follow the accepted ADR: all-rights-reserved distribution for Craig’s original code | Verify provenance before importing. Preserve third-party terms and rights already granted for earlier GPL copies. |
| D2 | Verify ownership and provenance before each import | Record donor URL, immutable revision, selected paths and third-party components in the extraction manifest. Unresolved provenance blocks the affected paths. An author name alone is not evidence of rights. |
| D3 | Defer presentation tools; decide placement when needed | PixelLab, MapTexture and Map Studio GUI remain outside the first extract. No provider or spending calls are authorized. |
| D4 | Use Feudal Frontiers’ existing repository workflow | Leave donor forge and agent scripts behind. Adapt the imported AGENTS.md to the target workflow while preserving mapgen’s technical rules. |
| D5 | Keep the older AMPB GameStart React design as historical reference | Leave ADR 0006 in the donor and link it as historical context. Follow the current Feudal Frontiers game plan; do not revive the older client design by importing it. |

## Extract order (after provenance verification)

1. Apply D1 and complete D2 for the selected paths. Record the approved terms and
   retained notices in the extraction manifest. Unresolved provenance blocks the affected
   import; merging this inventory does not clear that gate.
2. Import the approved **Move** and **Move (rework)** rows across MAP.md §§1–2,
   including the planning pack, ADRs, spec packs and AGENTS.md. Preserve history and
   relative layout; include the licence/provenance records approved under §5.
3. Complete the import-time rework before validation: remove the complete deferred
   PixelLab dependency set and rework shared startup/test wiring (MAP.md §2.1), retain
   stage-manifest tests (§2.3), and adapt AGENTS.md to the existing target workflow (D4).
4. Install the prerequisites recorded in `docs/environment.md` and restore project
   dependencies. Build the legacy stage binaries (at minimum `MapGenerator/Tiler/build.sh`;
   see MAP.md §2.2). From `apps/mapgen/`, run `just quality`, `dotnet test`,
   `dafny verify specs/**/*.dfy`, `npm run bdd:legacy`, and `npm run bdd:net`.
   Record exact results and any baseline failures; do not label a failing gate as passed.
   Any unexpected difference from the donor requires investigation before acceptance.
5. Pick up the **Defer** rows (MAP.md §4) as separate tickets when needed.
