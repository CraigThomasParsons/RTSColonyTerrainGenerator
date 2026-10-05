import { describe, expect, it } from "vitest";

import { FOREST_TERRAIN_TILES, FOREST_TREE_AUTOTILE } from "./forestTileset.ts";
import {
  cornerMask,
  edgeNeighbours,
  resolveAutotile,
  resolveAutotileMask,
  resolveTerrainTile,
  type AutotileConfig,
  type EdgeNeighbours,
} from "./tileResolver.ts";

/**
 * The resolver is the unit where autotiling correctness is asserted. Each test states a
 * neighbourhood and the sheet cell it must draw, read straight from AMPB's vendored tree
 * table, so a wrong bit fails as a named case rather than an odd-looking coastline.
 */

const none: EdgeNeighbours = { n: false, e: false, s: false, w: false };
const edges = (spec: string): EdgeNeighbours => ({
  n: spec.includes("N"),
  e: spec.includes("E"),
  s: spec.includes("S"),
  w: spec.includes("W"),
});

describe("cornerMask — AMPB's rule, verbatim", () => {
  it.each([
    ["N+W sets only UL", "NW", 8],
    ["N+E sets only UR", "NE", 4],
    ["S+E sets only LR", "SE", 2],
    ["S+W sets only LL", "SW", 1],
    ["all four edges set every corner", "NESW", 15],
    ["N+E+S sets UR and LR", "NES", 6],
  ])("%s", (_label, spec, mask) => {
    expect(cornerMask(edges(spec))).toBe(mask);
  });

  it.each(["", "N", "E", "S", "W", "NS", "EW"])(
    "sets no corner when no two adjacent edges match (%s)",
    (spec) => {
      // A corner needs both of its edges. Opposite edges never share a corner.
      expect(cornerMask(edges(spec))).toBe(0);
    },
  );
});

describe("edgeNeighbours", () => {
  it("treats off-grid neighbours as absent, even if the occupancy claims them", () => {
    const everywhere = () => true;

    expect(edgeNeighbours(everywhere, 0, 0, 3, 3)).toEqual({ n: false, e: true, s: true, w: false });
    expect(edgeNeighbours(everywhere, 2, 2, 3, 3)).toEqual({ n: true, e: false, s: false, w: true });
    expect(edgeNeighbours(everywhere, 1, 1, 3, 3)).toEqual({ n: true, e: true, s: true, w: true });
  });
});

/**
 * Every corner mask between 1 and 14 that edges can produce, with the edge set that
 * produces it. The other six (5, 7, 10, 11, 13, 14) each imply all four edges, which makes
 * mask 15. They are still entries in AMPB's table and are asserted by direct lookup below.
 */
const MASK_CASES: Array<[mask: number, spec: string]> = [
  [1, "SW"],
  [2, "SE"],
  [3, "ESW"],
  [4, "NE"],
  [6, "NES"],
  [8, "NW"],
  [9, "NSW"],
  [12, "NEW"],
];

describe("resolveAutotile — trees, against AMPB's vendored table", () => {
  it.each(MASK_CASES)("mask %i (%s) draws tileMap[mask]", (mask, spec) => {
    const neighbours = edges(spec);
    expect(cornerMask(neighbours)).toBe(mask);

    expect(resolveAutotile(FOREST_TREE_AUTOTILE, neighbours, 3, 4)).toEqual({
      kind: "sprite",
      cell: FOREST_TREE_AUTOTILE.tileMap[mask],
    });
  });

  it.each(Array.from({ length: 14 }, (_, index) => index + 1))(
    "mask %i, looked up directly, draws tileMap[mask] inside the 16 x 20 sheet",
    (mask) => {
      // Covers the six masks the edge rule cannot produce (5, 7, 10, 11, 13, 14), so a
      // malformed entry anywhere in the table is still a named failure.
      const cell = FOREST_TREE_AUTOTILE.tileMap[mask];
      expect(resolveAutotileMask(FOREST_TREE_AUTOTILE, mask, none, 0, 0)).toEqual({
        kind: "sprite",
        cell,
      });

      const [row, col] = cell ?? [-1, -1];
      expect(row).toBeGreaterThanOrEqual(0);
      expect(row).toBeLessThan(20);
      expect(col).toBeGreaterThanOrEqual(0);
      expect(col).toBeLessThan(16);
    },
  );

  it("routes mask 0 to singleTree and mask 15 to the interior variants, never to tileMap", () => {
    expect(FOREST_TREE_AUTOTILE.tileMap).toHaveLength(16);
    const isolated = FOREST_TREE_AUTOTILE.singleTree?.find((c) => c.label === "isolated");

    expect(resolveAutotileMask(FOREST_TREE_AUTOTILE, 0, none, 0, 0)).toEqual({
      kind: "sprite",
      cell: isolated?.sprite,
    });
    expect(resolveAutotileMask(FOREST_TREE_AUTOTILE, 15, none, 0, 0)).toEqual({
      kind: "sprite",
      cell: FOREST_TREE_AUTOTILE.interiorVariants?.[0],
    });
  });

  it("mask 15 picks an interior variant by AMPB's position hash, (row * 7 + col * 13) % n", () => {
    const variants = FOREST_TREE_AUTOTILE.interiorVariants ?? [];
    expect(variants.length).toBeGreaterThan(0);

    for (const [x, y] of [[0, 0], [1, 0], [0, 1], [5, 9], [17, 3]] as const) {
      expect(resolveAutotile(FOREST_TREE_AUTOTILE, edges("NESW"), x, y)).toEqual({
        kind: "sprite",
        cell: variants[(y * 7 + x * 13) % variants.length],
      });
    }
  });

  it("mask 15 falls back to tileMap[15] when there are no interior variants", () => {
    const { interiorVariants: _ignored, ...plain } = FOREST_TREE_AUTOTILE;

    expect(resolveAutotile(plain, edges("NESW"), 0, 0)).toEqual({
      kind: "sprite",
      cell: FOREST_TREE_AUTOTILE.tileMap[15],
    });
  });

  it.each([
    ["isolated", ""],
    ["N only", "N"],
    ["S only", "S"],
    ["N+S", "NS"],
    ["E only", "E"],
    ["W only", "W"],
    ["E+W", "EW"],
  ])("mask 0, %s, draws the matching singleTree sprite", (label, spec) => {
    const expected = FOREST_TREE_AUTOTILE.singleTree?.find((candidate) => candidate.label === label);
    expect(expected).toBeDefined();

    expect(resolveAutotile(FOREST_TREE_AUTOTILE, edges(spec), 0, 0)).toEqual({
      kind: "sprite",
      cell: expected?.sprite,
    });
  });

  it("mask 0 with no matching singleTree case takes the last case, as AMPB does", () => {
    const config: AutotileConfig = {
      tileMap: FOREST_TREE_AUTOTILE.tileMap,
      singleTree: [
        { label: "N only", hasN: true, hasS: false, hasE: false, hasW: false, sprite: [1, 1] },
        { label: "catch-all", hasN: false, hasS: false, hasE: false, hasW: false, sprite: [2, 2] },
      ],
    };

    expect(resolveAutotile(config, edges("EW"), 0, 0)).toEqual({ kind: "sprite", cell: [2, 2] });
  });

  it("mask 0 uses tileMap[0] for a config with no singleTree table (roads, stones)", () => {
    const config: AutotileConfig = { tileMap: [[7, 7]] };

    expect(resolveAutotile(config, none, 0, 0)).toEqual({ kind: "sprite", cell: [7, 7] });
  });

  it("is unmapped, not guessed, when the config is missing or has no entry for the mask", () => {
    expect(resolveAutotile(undefined, edges("NE"), 0, 0)).toEqual({ kind: "unmapped" });
    expect(resolveAutotile({ tileMap: [[0, 0]] }, edges("NE"), 0, 0)).toEqual({ kind: "unmapped" });
  });
});

describe("resolveTerrainTile", () => {
  it.each(Object.keys(FOREST_TERRAIN_TILES))("draws a configured cell for %s", (kind) => {
    expect(resolveTerrainTile(FOREST_TERRAIN_TILES, kind)).toEqual({
      kind: "sprite",
      cell: FOREST_TERRAIN_TILES[kind],
    });
  });

  it("covers every terrain kind the flat palette knows", async () => {
    const { TERRAIN_COLORS } = await import("./drawPreview.ts");
    expect(Object.keys(FOREST_TERRAIN_TILES).sort()).toEqual(Object.keys(TERRAIN_COLORS).sort());
  });

  it("flags a kind it has no cell for rather than substituting one", () => {
    expect(resolveTerrainTile(FOREST_TERRAIN_TILES, "lava")).toEqual({ kind: "unmapped" });
    expect(resolveTerrainTile(FOREST_TERRAIN_TILES, "toString")).toEqual({ kind: "unmapped" });
    expect(resolveTerrainTile(FOREST_TERRAIN_TILES, undefined)).toEqual({ kind: "unmapped" });
  });
});
