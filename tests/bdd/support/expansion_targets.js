// Target adapters for the cell-to-tile contract. Both answer:
//   { ok: true, tiles: [{x,y}...], tileMap: {width,height} } or { ok: false, error }
//
// net    — MapGen.Cli expand-cell via the shared driver.
// legacy — a Probe of the real published Tiler: ONLY the probed cell carries terrain 3
//          (RockMountain, max legal value); the four tiles whose id high byte carries it
//          (tileId = terrain << 8 | mask) ARE the legacy answer to "which tiles came
//          from this cell". Synthesis/run/parse live in the probe module.
import { runCliJson } from "./net_cli.js";
import { runTilerProbe } from "./legacy_tiler_probe.js";

export function expandViaNet(width, height, x, y) {
  const result = runCliJson("expand-cell", [
    "--width", String(width), "--height", String(height), "--x", String(x), "--y", String(y),
  ]);
  if (!result.ok) {
    return result;
  }
  return { ok: true, tiles: result.tiles, tileMap: { width: width * 2, height: height * 2 } };
}

export function expandViaLegacy(width, height, x, y) {
  const MARKER = 3;
  const terrain = new Array(width * height).fill(1);
  terrain[y * width + x] = MARKER;

  const probe = runTilerProbe({ width, height, terrain });
  const tiles = [];
  for (let ty = 0; ty < probe.tileHeight; ty++) {
    for (let tx = 0; tx < probe.tileWidth; tx++) {
      if (probe.idAt(tx, ty) >> 8 === MARKER) {
        tiles.push({ x: tx, y: ty });
      }
    }
  }
  return { ok: true, tiles, tileMap: { width: probe.tileWidth, height: probe.tileHeight } };
}
