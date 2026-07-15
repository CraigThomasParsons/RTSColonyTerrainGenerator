// Target adapters for the cell-to-tile contract — one per profile, same answer shape:
//   { ok: true, tiles: [{x,y}...], tileMap: {width,height} } or { ok: false, error }
//
// net    — drives the real C# implementation through MapGen.Cli.
// legacy — drives the real published Tiler binary: synthesizes a heightmap in which
//          ONLY the probed cell carries terrain 3 (RockMountain, the max legal value;
//          everything else terrain 1), runs the binary, and reads back which tile
//          coordinates carry that terrain in their tile-id high byte
//          (tileId = terrain << 8 | mask — TileIdResolver.cs). The four marked tiles
//          ARE the legacy pipeline's answer to "which tiles came from this cell".
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const REPO_ROOT = process.cwd();
const CLI_PROJECT = path.join(REPO_ROOT, "src", "MapGen.Cli");
const TILER_BINARY = path.join(REPO_ROOT, "MapGenerator", "Tiler", "bin", "published", "Tiler");

export function expandViaNet(width, height, x, y) {
  let stdout;
  try {
    stdout = execFileSync(
      "dotnet",
      ["run", "--project", CLI_PROJECT, "--no-build", "--",
        "expand-cell", "--width", String(width), "--height", String(height),
        "--x", String(x), "--y", String(y)],
      { encoding: "utf8", timeout: 60_000 },
    );
  } catch (err) {
    // Non-zero exit: the CLI still prints a JSON error line on stdout.
    const line = String(err.stdout ?? "").trim();
    if (line.length > 0) {
      return { ok: false, error: JSON.parse(line).error };
    }
    throw new Error(`MapGen.Cli failed without JSON output (run 'just build' first?): ${err.message}`);
  }
  const payload = JSON.parse(stdout.trim());
  return { ok: true, tiles: payload.tiles, tileMap: { width: width * 2, height: height * 2 } };
}

export function expandViaLegacy(width, height, x, y) {
  const MARKER = 3; // RockMountain — max legal terrain byte
  const cellCount = width * height;

  // .heightmap: u32 width, u32 height, u64 seed, u8 heights[N], u8 terrain[N] (row-major).
  const buffer = Buffer.alloc(16 + 2 * cellCount);
  buffer.writeUInt32LE(width, 0);
  buffer.writeUInt32LE(height, 4);
  buffer.writeBigUInt64LE(1n, 8);
  buffer.fill(128, 16, 16 + cellCount);          // flat heights
  buffer.fill(1, 16 + cellCount);                 // terrain: Land everywhere...
  buffer[16 + cellCount + y * width + x] = MARKER; // ...except the probed cell

  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "cell-to-tile-legacy-"));
  try {
    const jobId = `probe-${x}-${y}`;
    const input = path.join(workDir, `${jobId}.heightmap`);
    fs.writeFileSync(input, buffer);
    execFileSync(TILER_BINARY, [input], { cwd: workDir, timeout: 60_000, stdio: "pipe" });

    const out = fs.readFileSync(path.join(workDir, "outbox", `${jobId}.maptiles`));
    if (out.toString("latin1", 0, 4) !== "MTIL") {
      throw new Error("legacy Tiler produced an artifact without the MTIL magic");
    }
    const tileWidth = out.readUInt32LE(8);
    const tileHeight = out.readUInt32LE(12);

    const tiles = [];
    for (let ty = 0; ty < tileHeight; ty++) {
      for (let tx = 0; tx < tileWidth; tx++) {
        const id = out.readUInt16LE(32 + 2 * (ty * tileWidth + tx));
        if (id >> 8 === MARKER) {
          tiles.push({ x: tx, y: ty });
        }
      }
    }
    return { ok: true, tiles, tileMap: { width: tileWidth, height: tileHeight } };
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}
