/**
 * Which cell of the forest sheet a preview tile draws. This module is pure: no canvas, no
 * image, no I/O. Autotiling correctness is asserted here.
 *
 * This is a port, not a derivation. The tree mapping is AMPB's own data, vendored in
 * `third_party/ampb_forest_tileset/` (see its PROVENANCE.md). The mask rule is AMPB's
 * verbatim, from `TreeAutotiler::computeMask` and `trees.ts`. If the rule drifted from the
 * game's, the preview would stop showing what the game shows.
 */

/** `[row, col]` in the sheet, the convention AMPB's configs use. */
export type SpriteCell = readonly [row: number, col: number];

/** One `singleTree` case: the sprite for a mask-zero tile with exactly these edge neighbours. */
export interface SingleTileCase {
  label: string;
  hasN: boolean;
  hasS: boolean;
  hasE: boolean;
  hasW: boolean;
  sprite: SpriteCell;
}

/** One `AutotileConfig` row, in the shape `AutotileConfig::toFrontendArray()` emits. */
export interface AutotileConfig {
  tileMap: readonly SpriteCell[];
  interiorVariants?: readonly SpriteCell[];
  singleTree?: readonly SingleTileCase[];
  removedTile?: SpriteCell;
}

/** Edge neighbours of one tile. Off-grid neighbours are absent. */
export interface EdgeNeighbours {
  n: boolean;
  e: boolean;
  s: boolean;
  w: boolean;
}

/**
 * Either a cell to blit, or a flag that nothing is configured. The flag is never a
 * plausible substitute: the caller paints the unknown colour, so a gap in the palette
 * shows up as a gap.
 */
export type TileResolution =
  | { kind: "sprite"; cell: SpriteCell }
  | { kind: "unmapped" };

const UNMAPPED: TileResolution = { kind: "unmapped" };

/** Corner bits, AMPB's layout. A corner is set only when both of its edges match. */
export const CORNER_UL = 8;
export const CORNER_UR = 4;
export const CORNER_LR = 2;
export const CORNER_LL = 1;
export const ALL_CORNERS = CORNER_UL | CORNER_UR | CORNER_LR | CORNER_LL;

export function cornerMask({ n, e, s, w }: EdgeNeighbours): number {
  let mask = 0;
  if (n && w) {
    mask |= CORNER_UL;
  }
  if (n && e) {
    mask |= CORNER_UR;
  }
  if (s && e) {
    mask |= CORNER_LR;
  }
  if (s && w) {
    mask |= CORNER_LL;
  }
  return mask;
}

/**
 * Edge neighbours of `(x, y)` within a `width` x `height` grid. Anything off the grid is
 * absent, even if `occupied` claims otherwise. Map borders therefore resolve the same way
 * every time.
 */
export function edgeNeighbours(
  occupied: (x: number, y: number) => boolean,
  x: number,
  y: number,
  width: number,
  height: number,
): EdgeNeighbours {
  const at = (nx: number, ny: number) =>
    nx >= 0 && ny >= 0 && nx < width && ny < height && occupied(nx, ny);

  return { n: at(x, y - 1), e: at(x + 1, y), s: at(x, y + 1), w: at(x - 1, y) };
}

/**
 * Resolve one autotiled tile, following AMPB's tree rule:
 *
 * - mask 15 picks an interior variant at `(row * 7 + col * 13) % count`, AMPB's
 *   position hash. That keeps it deterministic and the same as the game.
 * - mask 0 picks the `singleTree` case whose N/S/E/W flags match exactly. If none
 *   matches, it takes the last case, the "isolated" catch-all. With no `singleTree`
 *   table it uses `tileMap[0]`.
 * - otherwise it uses `tileMap[mask]`.
 *
 * A missing config, or a mask with no entry, is unmapped.
 */
export function resolveAutotile(
  config: AutotileConfig | undefined,
  neighbours: EdgeNeighbours,
  x: number,
  y: number,
): TileResolution {
  return resolveAutotileMask(config, cornerMask(neighbours), neighbours, x, y);
}

/**
 * The table lookup behind `resolveAutotile`, keyed by an explicit mask. Six masks (5, 7,
 * 10, 11, 13, 14) can never come out of `cornerMask`: each one implies all four edges, and
 * four edges make 15. They are still entries in AMPB's table, and this is where they are
 * reachable and tested. `neighbours` matters only for the mask-zero `singleTree` cases.
 */
export function resolveAutotileMask(
  config: AutotileConfig | undefined,
  mask: number,
  neighbours: EdgeNeighbours,
  x: number,
  y: number,
): TileResolution {
  if (!config) {
    return UNMAPPED;
  }

  if (mask === ALL_CORNERS && config.interiorVariants && config.interiorVariants.length > 0) {
    const variants = config.interiorVariants;
    return spriteOrUnmapped(variants[(y * 7 + x * 13) % variants.length]);
  }

  if (mask === 0 && config.singleTree && config.singleTree.length > 0) {
    const cases = config.singleTree;
    const match = cases.find(
      (candidate) =>
        candidate.hasN === neighbours.n &&
        candidate.hasS === neighbours.s &&
        candidate.hasE === neighbours.e &&
        candidate.hasW === neighbours.w,
    );
    return spriteOrUnmapped((match ?? cases[cases.length - 1])?.sprite);
  }

  return spriteOrUnmapped(config.tileMap[mask]);
}

/** A plain terrain kind is one fixed cell, with no blending. An unknown kind is unmapped. */
export function resolveTerrainTile(
  terrainTiles: Readonly<Record<string, SpriteCell>>,
  kind: string | undefined,
): TileResolution {
  if (kind === undefined || !Object.hasOwn(terrainTiles, kind)) {
    return UNMAPPED;
  }
  return spriteOrUnmapped(terrainTiles[kind]);
}

function spriteOrUnmapped(cell: SpriteCell | undefined): TileResolution {
  if (!cell) {
    return UNMAPPED;
  }
  return { kind: "sprite", cell };
}
