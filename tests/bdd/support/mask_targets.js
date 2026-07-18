// Target adapters for the adjacency-mask contract. Both answer:
//   { ok: true, mask: <0..15> } or { ok: false, error }
//
// net    — MapGen.Cli mask-cell via the shared driver.
// legacy — a Probe of the real published Tiler: the mask is the tile-id LOW NIBBLE
//          (tileId = terrain << 8 | mask); the cell (x,y) owns tile (2x,2y).
import { runCliJson } from "./net_cli.js";
import { runTilerProbe } from "./legacy_tiler_probe.js";

export function maskViaNet(width, height, x, y, terrainRowMajor) {
  const result = runCliJson("mask-cell", [
    "--width", String(width), "--height", String(height), "--x", String(x), "--y", String(y),
    "--terrain", terrainRowMajor.join(","),
  ]);
  // Failures pass through untouched; successes are narrowed to the mask alone.
  if (!result.ok) {
    return result;
  }
  return { ok: true, mask: result.mask };
}

export function maskViaLegacy(width, height, x, y, terrainRowMajor) {
  const probe = runTilerProbe({ width, height, terrain: terrainRowMajor });
  return { ok: true, mask: probe.idAt(2 * x, 2 * y) & 0x0f };
}
