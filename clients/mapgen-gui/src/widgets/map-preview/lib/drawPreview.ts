import type { MapPreview } from "~/shared/api/contract.ts";

/**
 * Paints a `MapPreview` into a 2D context.
 *
 * Terrain is row-major (`index = y * width + x`) — the convention `TerrainGrid` already uses
 * and the one the preview payload is defined by — and the palette is `.worldpayload`'s
 * terrain vocabulary. Coordinates here are tile x/y, matching `.playable.json`; this is the
 * one document in the contract that speaks x/y rather than row/col.
 *
 * Deliberately a plain function over a context rather than a class over a canvas: the camera
 * transform is the engine's job (`MapPreviewSurface`), and what gets painted where is worth
 * testing without a GPU.
 */

/** `.worldpayload`'s terrain vocabulary, in the flat palette the prototype renders. */
export const TERRAIN_COLORS: Record<string, string> = {
  deep_water: "#16394f",
  water: "#2e6f8e",
  dirt: "#8a6b45",
  grass: "#3f6b2f",
  rock: "#6f6f6d",
  mountain: "#9c958c",
};

/** A palette name this client has not been taught. Flagged, never dropped. */
export const UNKNOWN_TERRAIN_COLOR = "#ff00ff";

/**
 * TreePlanter's canopy. Darker than `grass` so a forest reads as a forest against the
 * clearings around it, and desaturated enough that the resource markers still carry.
 */
export const TREE_COLOR = "#22421c";

/**
 * Harvestable types this client has a colour for. No oil: that is a Warcraft 2 resource and
 * has no place in this game's economy. The generator currently emits only `wood` and `ore`;
 * `gold` and `stone` are held for the economy this game does have.
 */
const RESOURCE_COLORS: Record<string, string> = {
  wood: "#2f8f4f",
  gold: "#e0b23c",
  stone: "#b8b2a6",
};

const UNKNOWN_RESOURCE_COLOR = "#ff00ff";
const START_ZONE_COLOR = "#f2f2f2";
const START_ZONE_RING_COLOR = "#12121a";

export interface DrawPreviewOptions {
  /** Pixel size of one preview tile. The world is `width * tileSize` pixels across. */
  tileSize: number;
  /** Present only for an explicitly human-approved candidate. */
  approvedBackground?: CanvasImageSource | undefined;
}

export function drawPreview(
  ctx: CanvasRenderingContext2D,
  preview: MapPreview,
  { tileSize, approvedBackground }: DrawPreviewOptions,
): void {
  const expected = preview.width * preview.height;
  if (preview.terrain.length !== expected) {
    // A short array would draw a map that is silently wrong — worse than one that refuses.
    throw new Error(
      `Preview terrain has ${preview.terrain.length} entries but the grid is ` +
        `${preview.width} x ${preview.height} (${expected} expected).`,
    );
  }

  // Back to front. The order is the contract: the two grid layers go down first, so a
  // forest can never hide the start zones and resource clusters the preview exists to show.
  if (approvedBackground) {
    ctx.drawImage(approvedBackground, 0, 0, preview.width * tileSize, preview.height * tileSize);
  } else {
    drawTerrain(ctx, preview, tileSize);
    drawCanopy(ctx, preview, tileSize);
  }
  drawResourceClusters(ctx, preview, tileSize);
  drawStartZones(ctx, preview, tileSize);
}

function drawTerrain(
  ctx: CanvasRenderingContext2D,
  preview: MapPreview,
  tileSize: number,
): void {
  const colors = preview.terrain_palette.map(
    (name) => TERRAIN_COLORS[name] ?? UNKNOWN_TERRAIN_COLOR,
  );

  for (let y = 0; y < preview.height; y += 1) {
    for (let x = 0; x < preview.width; x += 1) {
      const paletteIndex = preview.terrain[y * preview.width + x] ?? -1;
      ctx.fillStyle = colors[paletteIndex] ?? UNKNOWN_TERRAIN_COLOR;
      ctx.fillRect(x * tileSize, y * tileSize, tileSize, tileSize);
    }
  }
}

/** Grid layer at terrain scale (with `drawTerrain`), not a marker. */
function drawCanopy(
  ctx: CanvasRenderingContext2D,
  preview: MapPreview,
  tileSize: number,
): void {
  ctx.fillStyle = TREE_COLOR;

  for (const tree of preview.trees) {
    ctx.fillRect(tree.x * tileSize, tree.y * tileSize, tileSize, tileSize);
  }
}

function drawResourceClusters(
  ctx: CanvasRenderingContext2D,
  preview: MapPreview,
  tileSize: number,
): void {
  const size = Math.max(2, tileSize * 1.5);
  const half = size / 2;

  for (const cluster of preview.resource_clusters) {
    ctx.fillStyle = RESOURCE_COLORS[cluster.type] ?? UNKNOWN_RESOURCE_COLOR;
    ctx.fillRect(
      cluster.x * tileSize + tileSize / 2 - half,
      cluster.y * tileSize + tileSize / 2 - half,
      size,
      size,
    );
  }
}

function drawStartZones(
  ctx: CanvasRenderingContext2D,
  preview: MapPreview,
  tileSize: number,
): void {
  const radius = Math.max(3, tileSize * 1.25);

  for (const zone of preview.start_zones) {
    const centreX = zone.x * tileSize + tileSize / 2;
    const centreY = zone.y * tileSize + tileSize / 2;

    ctx.beginPath();
    ctx.arc(centreX, centreY, radius, 0, Math.PI * 2);
    ctx.fillStyle = START_ZONE_COLOR;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(centreX, centreY, radius, 0, Math.PI * 2);
    ctx.strokeStyle = START_ZONE_RING_COLOR;
    ctx.lineWidth = Math.max(1, tileSize / 4);
    ctx.stroke();
  }
}
