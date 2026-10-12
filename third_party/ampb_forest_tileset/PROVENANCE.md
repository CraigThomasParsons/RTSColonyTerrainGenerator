# Provenance — AMPB forest tileset

A vendored snapshot of AgileMedievalPeasantBoard's (AMPB's) forest terrain sheet and
autotile mappings. The map studio's tiled preview draws from it (issue #67), so it does
not need AMPB to be running.

| | |
|---|---|
| Upstream | AgileMedievalPeasantBoard, the local clone at `~/Code/AgileMedievalPeasantBoard` |
| Commit | `795f5c5462b695a94dd4c60ae1040e8555ce5649` (branch `chore/docblock-backfill-20261005-0800`) |
| Captured on | 2026-10-05 |
| Captured by | agent, for Gitea issue #67 |

## Files

| File | Source in AMPB | Notes |
|---|---|---|
| `terrain.png` | `public/game/assets/tilesets/forest/terrain.png` | Byte-for-byte copy. 256×320, a 16-column × 20-row grid of 16px tiles. sha256 `18dd695c085785bc3805d8fc28d8cfd11a24fbf5f7a076605b7e09c652d4771d`. |
| `autotile-configs.json` | `database/seeders/AutotileConfigSeeder.php` | The `tree`, `road` and `stone` rows transcribed into the shape `AutotileConfig::toFrontendArray()` produces (`tileMap`, plus `interiorVariants`, `singleTree` and `removedTile` when present). Every sprite is `[row, col]` in `terrain.png`. |

### Why the seeder and not the JSON files or the live API

AMPB keeps the mappings in the `autotile_configs` table. It serves them at
`/api/autotile-configs` and injects them into the game as `window.RTS_AUTOTILE`. The
seeder is the committed source of that table.
`resources/game/data/autotile.json` and `tree_autotile.json` also exist, but no AMPB
code reads them any more, and they disagree with the seeder and with each other. No
AMPB process was running when this snapshot was taken, so the live API could not be
queried. **Edits made through AMPB's sprite editors (`/tiler`) after seeding are not in
this snapshot.**

### Not vendored

- `conifer_terrain.png` and `chopped_tree.png`. AMPB's game does not draw trees from
  the conifer strip: `TreeAutotiler` and `trees.ts` both resolve tree sprites to cells of
  `terrain.png`. Copying art that nothing draws would add licensing exposure for no
  benefit.
- The swamp and dungeon tilesets. Issue #67 covers the forest only.

## Drift

The snapshot is deliberately frozen. To refresh it, re-copy `terrain.png`, re-transcribe
the seeder (or, better, save `GET /api/autotile-configs` from a running AMPB), and update
the commit and date above. Drift shows up two ways: the sha256 above against AMPB's
file, and a diff of `autotile-configs.json` against AMPB's seeder or API. Refreshing is
a deliberate act, never automatic.

## Licensing position — unresolved, on the record

The sheet is **Warcraft-1-derived art**. AMPB's repository carries it, but no licence in
either repository grants the right to redistribute it. Copying it here is a
redistribution decision, not a technical one. Issue #67 (Further Notes) flags this as
unsettled and chose the vendored copy over a runtime fetch from AMPB on coupling
grounds. Before this directory merges, the human reviewer should confirm that a second
copy is acceptable. That matters most for any public mirror of this repository, which
would publish the art. If it is not acceptable, the alternative the issue names is to
fetch the sheet from a running AMPB instead. The client imports this directory in one
place (`clients/mapgen-gui/src/widgets/map-preview/lib/forestTileset.ts`), and its
loader is injected, so swapping the source is a one-module change. At runtime a sheet
that fails to load already degrades the preview to flat colour.

`autotile-configs.json` is AMPB's own data (sprite coordinates), not art.
