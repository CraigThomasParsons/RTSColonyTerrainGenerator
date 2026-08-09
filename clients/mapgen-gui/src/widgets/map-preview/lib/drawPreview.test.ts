import { describe, expect, it } from "vitest";

import type { MapPreview } from "~/shared/api/contract.ts";
import { drawPreview, TERRAIN_COLORS, TREE_COLOR, UNKNOWN_TERRAIN_COLOR } from "./drawPreview.ts";

/**
 * The seam under test is the draw call: given a `MapPreview` and a 2D context, what gets
 * painted where. A recording context is used rather than a real canvas because jsdom has no
 * canvas backend, and because the assertion worth making is about the row-major terrain
 * convention, not about pixels the browser produced.
 */
interface DrawnRect {
  fillStyle: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DrawnArc {
  fillStyle: string;
  x: number;
  y: number;
  radius: number;
}

const recordingContext = () => {
  const rects: DrawnRect[] = [];
  const arcs: DrawnArc[] = [];
  let pendingArc: Omit<DrawnArc, "fillStyle"> | null = null;

  const ctx = {
    fillStyle: "",
    strokeStyle: "",
    lineWidth: 1,
    save: () => {},
    restore: () => {},
    beginPath: () => {},
    closePath: () => {},
    stroke: () => {},
    clearRect: () => {},
    fillRect(x: number, y: number, w: number, h: number) {
      rects.push({ fillStyle: ctx.fillStyle, x, y, w, h });
    },
    strokeRect: () => {},
    arc(x: number, y: number, radius: number) {
      pendingArc = { x, y, radius };
    },
    fill() {
      if (pendingArc) {
        arcs.push({ fillStyle: ctx.fillStyle, ...pendingArc });
        pendingArc = null;
      }
    },
  };

  return { ctx: ctx as unknown as CanvasRenderingContext2D, rects, arcs };
};

const TILE_SIZE = 8;

const previewOf = (overrides: Partial<MapPreview> = {}): MapPreview => ({
  version: 2,
  job_id: "43860dcf-6469-42a7-9843-4e33abeacfac",
  width: 3,
  height: 2,
  terrain_palette: ["deep_water", "water", "dirt", "grass", "rock", "mountain"],
  // Row 0: deep_water, water, dirt   Row 1: grass, rock, mountain
  terrain: [0, 1, 2, 3, 4, 5],
  trees: [],
  start_zones: [],
  resource_clusters: [],
  ...overrides,
});

describe("drawPreview", () => {
  it("paints every terrain tile row-major, at index = y * width + x", () => {
    const { ctx, rects } = recordingContext();

    drawPreview(ctx, previewOf(), { tileSize: TILE_SIZE });

    const tiles = rects.filter((rect) => rect.w === TILE_SIZE && rect.h === TILE_SIZE);
    expect(tiles).toHaveLength(6);

    // (x=2, y=0) is terrain index 2 -> "dirt", drawn at (2*8, 0*8).
    expect(tiles[2]).toEqual({
      fillStyle: TERRAIN_COLORS.dirt,
      x: 2 * TILE_SIZE,
      y: 0,
      w: TILE_SIZE,
      h: TILE_SIZE,
    });

    // (x=0, y=1) is terrain index 3 -> "grass", drawn at (0, 1*8).
    expect(tiles[3]).toEqual({
      fillStyle: TERRAIN_COLORS.grass,
      x: 0,
      y: 1 * TILE_SIZE,
      w: TILE_SIZE,
      h: TILE_SIZE,
    });
  });

  it("paints a terrain name it does not know rather than dropping the tile", () => {
    // The palette is server-side vocabulary and may gain a name before this client does.
    // A missing tile would read as a hole in the map; a flagged colour reads as news.
    const { ctx, rects } = recordingContext();

    drawPreview(
      ctx,
      previewOf({
        width: 1,
        height: 1,
        terrain_palette: ["lava"],
        terrain: [0],
      }),
      { tileSize: TILE_SIZE },
    );

    const tiles = rects.filter((rect) => rect.w === TILE_SIZE);
    expect(tiles).toHaveLength(1);
    expect(tiles[0]?.fillStyle).toBe(UNKNOWN_TERRAIN_COLOR);
  });

  it("marks each start zone at the centre of its tile, on top of the terrain", () => {
    const { ctx, arcs } = recordingContext();

    drawPreview(
      ctx,
      previewOf({ start_zones: [{ id: "start_1", x: 2, y: 1 }] }),
      { tileSize: TILE_SIZE },
    );

    expect(arcs).toHaveLength(1);
    expect(arcs[0]?.x).toBe(2 * TILE_SIZE + TILE_SIZE / 2);
    expect(arcs[0]?.y).toBe(1 * TILE_SIZE + TILE_SIZE / 2);
  });

  it("marks resource clusters by type", () => {
    const { ctx, rects } = recordingContext();

    drawPreview(
      ctx,
      previewOf({
        resource_clusters: [
          { id: "start_1_wood", type: "wood", x: 1, y: 1, start_id: "start_1" },
          { id: "start_1_gold", type: "gold", x: 2, y: 0, start_id: "start_1" },
        ],
      }),
      { tileSize: TILE_SIZE },
    );

    const markers = rects.filter((rect) => rect.w !== TILE_SIZE);
    expect(markers).toHaveLength(2);
    expect(markers[0]?.fillStyle).not.toBe(markers[1]?.fillStyle);
  });

  it("paints each tree over its own terrain tile, at terrain scale", () => {
    const { ctx, rects } = recordingContext();

    drawPreview(
      ctx,
      previewOf({
        trees: [
          { x: 1, y: 0 },
          { x: 2, y: 1 },
        ],
      }),
      { tileSize: TILE_SIZE },
    );

    // Trees are a grid layer, not a marker: one covers exactly the tile it grows on.
    const canopy = rects.filter((rect) => rect.fillStyle === TREE_COLOR);
    expect(canopy).toEqual([
      { fillStyle: TREE_COLOR, x: 1 * TILE_SIZE, y: 0, w: TILE_SIZE, h: TILE_SIZE },
      { fillStyle: TREE_COLOR, x: 2 * TILE_SIZE, y: 1 * TILE_SIZE, w: TILE_SIZE, h: TILE_SIZE },
    ]);
  });

  it("paints the canopy under the resource and start-zone markers", () => {
    // A forest that covered the start zones would hide exactly what the preview is for.
    const { ctx, rects, arcs } = recordingContext();

    drawPreview(
      ctx,
      previewOf({
        trees: [{ x: 1, y: 1 }],
        resource_clusters: [
          { id: "start_1_wood", type: "wood", x: 1, y: 1, start_id: "start_1" },
        ],
        start_zones: [{ id: "start_1", x: 1, y: 1 }],
      }),
      { tileSize: TILE_SIZE },
    );

    // Walk backwards: the last canopy rect must still precede the first marker.
    let lastTreeIndex = -1;
    for (let index = rects.length - 1; index >= 0; index -= 1) {
      if (rects[index]?.fillStyle === TREE_COLOR) {
        lastTreeIndex = index;
        break;
      }
    }
    const firstMarkerIndex = rects.findIndex((rect) => rect.w !== TILE_SIZE);

    expect(lastTreeIndex).toBeGreaterThanOrEqual(0);
    expect(firstMarkerIndex).toBeGreaterThan(lastTreeIndex);
    expect(arcs).toHaveLength(1);
  });

  it("refuses a terrain array whose length disagrees with width * height", () => {
    // Row-major indexing is the whole contract of this payload. A short array would draw a
    // map that is silently wrong, which is worse than one that does not draw.
    const { ctx } = recordingContext();

    expect(() =>
      drawPreview(ctx, previewOf({ width: 3, height: 2, terrain: [0, 1, 2] }), {
        tileSize: TILE_SIZE,
      }),
    ).toThrow(/3 x 2/);
  });
});
