// Target adapters for the adjacency-mask contract — one per profile, same answer shape:
//   { ok: true, mask: <0..15> } or { ok: false, error }
//
// net    — drives the C# implementation through MapGen.Cli mask-cell.
// legacy — drives the real published Tiler binary: writes a heightmap with the given
//          terrain grid, runs the binary, and reads the target cell's mask out of a
//          tile-id's LOW NIBBLE (tileId = terrain << 8 | mask — TileIdResolver.cs). All
//          four of the cell's 2×2 tiles carry the same id, so any one of them serves.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const REPO_ROOT = process.cwd();
const CLI_PROJECT = path.join(REPO_ROOT, "src", "MapGen.Cli");
const TILER_BINARY = path.join(REPO_ROOT, "MapGenerator", "Tiler", "bin", "published", "Tiler");

export function maskViaNet(width, height, x, y, terrainRowMajor) {
  let stdout;
  try {
    stdout = execFileSync(
      "dotnet",
      ["run", "--project", CLI_PROJECT, "--no-build", "--",
        "mask-cell", "--width", String(width), "--height", String(height),
        "--x", String(x), "--y", String(y), "--terrain", terrainRowMajor.join(",")],
      { encoding: "utf8", timeout: 60_000 },
    );
  } catch (err) {
    const line = String(err.stdout ?? "").trim();
    if (line.length > 0) {
      return { ok: false, error: JSON.parse(line).error };
    }
    throw new Error(`MapGen.Cli failed without JSON output (run 'just build' first?): ${err.message}`);
  }
  return { ok: true, mask: JSON.parse(stdout.trim()).mask };
}

export function maskViaLegacy(width, height, x, y, terrainRowMajor) {
  const cellCount = width * height;

  // .heightmap: u32 width, u32 height, u64 seed, u8 heights[N], u8 terrain[N] (row-major).
  // Terrain bytes must be in 0..3 (HeightmapReader validates); the caller keeps to that.
  const buffer = Buffer.alloc(16 + 2 * cellCount);
  buffer.writeUInt32LE(width, 0);
  buffer.writeUInt32LE(height, 4);
  buffer.writeBigUInt64LE(1n, 8);
  buffer.fill(128, 16, 16 + cellCount);
  for (let i = 0; i < cellCount; i++) {
    buffer[16 + cellCount + i] = terrainRowMajor[i];
  }

  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "adjacency-mask-legacy-"));
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
    // The cell (x,y) owns tile (2x, 2y); read its id and take the low nibble = mask.
    const tileId = out.readUInt16LE(32 + 2 * (2 * y * tileWidth + 2 * x));
    return { ok: true, mask: tileId & 0x0f };
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}
