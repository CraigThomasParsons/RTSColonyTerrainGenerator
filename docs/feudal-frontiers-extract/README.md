# Feudal Frontiers Extract — Donor Notes (RTSColonyTerrainGenerator → `apps/mapgen`)

Status: **Inventory only** (Gitea #98, 2026-10-06). Nothing has been moved yet.

## Why this exists

The Feudal Frontiers monorepo plan puts terrain generation in `apps/mapgen` inside
`ElasticGun/feudal-frontiers`. That repository does not exist yet. These notes prepare the
extract from this donor repository, so the move is mechanical when the monorepo is ready
and nobody waits on the monorepo to start planning.

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
| this README | Purpose, ground rules, the open decisions for Craig, and the order to carry out the extract |

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

## Decisions needed from Craig

These are flagged, not decided. The extract must not proceed past step 1 below until the
licence decision is made.

| # | Decision | Options | Notes |
|---|---|---|---|
| D1 | **Licence of `apps/mapgen` inside the monorepo** | (a) keep GPL-2 for `apps/mapgen` and carry the `LICENSE` file into it; (b) Craig, as sole copyright holder, relicenses (a separate, explicit act, not part of this ticket); (c) keep mapgen out of the monorepo and integrate over the HTTP seam only | See MAP.md §5. This ticket changes no licence file. |
| D2 | Contributor check before any relicense | confirm every commit author is Craig or his agents | Required only for D1(b). See MAP.md §5.3. |
| D3 | Deferred presentation lanes (PixelLab, MapTexture, Map Studio GUI) | move later into `apps/mapgen`, or into a separate presentation app | ADR 0001-pixellab says they are presentation-only. They never affect gameplay. |
| D4 | Forge tooling (`scripts/tools/*gitea*`) | rewrite for the monorepo's Gitea, or reuse whatever process the monorepo already has | The scripts hard-code `craigpars/RTSColonyTerrainGenerator`. |
| D5 | ADR 0006 (GameStart React island) | hand it to the AMPB game extract ticket | Mostly about the AMPB side. See MAP.md §3. |

## Extract order (once the monorepo exists)

1. Settle D1 (licence). Until then, stop.
2. Import the **Move** rows of MAP.md §2 under `apps/mapgen/`, preserving history.
3. Build the legacy stage binaries (at minimum `MapGenerator/Tiler/build.sh`; see the
   *fresh-clone gotchas* in MAP.md §2.2). Then run the full gate surface from `apps/mapgen/`: `just quality`, `dotnet test`,
   `dafny verify specs/**/*.dfy`, `npm run bdd:legacy`, `npm run bdd:net`. They must pass
   with the same results as on the donor. Any change is a regression in the move itself.
4. Rewrite the monorepo-specific parts of `AGENTS.md` (issue lifecycle, forge URL, lock
   file). The coding and specification rules stay unchanged.
5. Pick up the **Defer** rows (MAP.md §4) as their own tickets.
