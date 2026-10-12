import autotileConfigs from "@ampb-tileset/autotile-configs.json";
import terrainSheetUrl from "@ampb-tileset/terrain.png";

import type { AutotileConfig, SpriteCell } from "./tileResolver.ts";

/**
 * The forest tileset as the preview draws it: a loaded sheet plus the tables that say
 * which cell to cut from it. Loading is a separate step from drawing. The draw path takes
 * an already-loaded `Tileset`, so tests can pass a stub and never touch the network or
 * the filesystem.
 */
export interface Tileset {
  image: CanvasImageSource;
  /** Edge length of one sheet cell, in source pixels. */
  sourceTileSize: number;
  /** AMPB's canopy autotile table. */
  tree: AutotileConfig | undefined;
  /** One plain cell per `.worldpayload` terrain kind. */
  terrain: Readonly<Record<string, SpriteCell>>;
}

/** A tileset source the widget can call. A rejection means the preview drops to flat colour. */
export type TilesetLoader = () => Promise<Tileset>;

/** AMPB's sheet is a 16 x 20 grid of 16px cells. */
export const FOREST_SOURCE_TILE_SIZE = 16;

/** AMPB's tree row, vendored verbatim. Road and stone are vendored but not drawn yet. */
export const FOREST_TREE_AUTOTILE: AutotileConfig = (
  autotileConfigs as unknown as Record<string, AutotileConfig>
).tree as AutotileConfig;

/**
 * Plain ground cells per terrain kind.
 *
 * **This table is this repository's choice, not AMPB's.** AMPB has autotile configs for
 * trees, roads and stones only. It has no terrain-kind mapping and no water or shoreline
 * table. Each entry is the cleanest solid cell in the forest sheet for that kind. The
 * sheet has one water fill, so `deep_water` and `water` look the same here (AMPB's
 * importer accepts no `deep_water` at all). There is no
 * shoreline blending until a tuned water table exists. A kind missing here renders as
 * the flagged unknown colour.
 */
export const FOREST_TERRAIN_TILES: Readonly<Record<string, SpriteCell>> = {
  deep_water: [10, 4],
  water: [8, 2],
  dirt: [19, 5],
  grass: [6, 1],
  rock: [11, 9],
  mountain: [4, 1],
};

/** Load the vendored forest sheet through an `Image`. Rejects if the browser cannot decode it. */
export const loadForestTileset: TilesetLoader = () =>
  new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () =>
      resolve({
        image,
        sourceTileSize: FOREST_SOURCE_TILE_SIZE,
        tree: FOREST_TREE_AUTOTILE,
        terrain: FOREST_TERRAIN_TILES,
      });
    image.onerror = () => reject(new Error(`Forest tileset failed to load from ${terrainSheetUrl}.`));
    image.src = terrainSheetUrl;
  });
