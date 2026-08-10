// The Legacy Tiler Probe — one deep module for asking the legacy baseline a behavioural
// question through its real binary and artifacts (CONTEXT.md: "Probe").
//
// Interface: runTilerProbe({ width, height, terrain }) -> { tileWidth, tileHeight, idAt }
//   terrain: row-major int[width*height], values 0..3 (the legacy heightmap range).
//   idAt(tx, ty): the u16 tile id at tile coordinates — callers interpret it
//   (tileId = terrain << 8 | mask, TileIdResolver.cs).
//
// Everything else — the .heightmap binary writer, the published-binary invocation, the
// .maptiles parser — is an INTERNAL seam of this module. When Epic 3 lands the verified
// C# codec, those internals can be replaced without touching any caller.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const REPO_ROOT = process.cwd();
const TILER_BINARY = path.join(REPO_ROOT, "MapGenerator", "Tiler", "bin", "published", "Tiler");

/** .heightmap layout: u32 width, u32 height, u64 seed, u8 heights[N], u8 terrain[N] (row-major). */
function writeHeightmapBuffer(width, height, terrain) {
  const cellCount = width * height;
  if (terrain.length !== cellCount) {
    throw new Error(`terrain length ${terrain.length} does not match ${width}×${height}`);
  }
  const buffer = Buffer.alloc(16 + 2 * cellCount);
  buffer.writeUInt32LE(width, 0);
  buffer.writeUInt32LE(height, 4);
  buffer.writeBigUInt64LE(1n, 8);
  buffer.fill(128, 16, 16 + cellCount); // flat heights — height is irrelevant to tiling probes
  for (let i = 0; i < cellCount; i++) {
    buffer[16 + cellCount + i] = terrain[i];
  }
  return buffer;
}

/** .maptiles layout: 32-byte header (MTIL, ver, tileW@8, tileH@12, seed, count, reserved), u16 ids row-major. */
function parseMapTiles(buf) {
  if (buf.toString("latin1", 0, 4) !== "MTIL") {
    throw new Error("legacy Tiler produced an artifact without the MTIL magic");
  }
  const tileWidth = buf.readUInt32LE(8);
  const tileHeight = buf.readUInt32LE(12);
  return {
    tileWidth,
    tileHeight,
    idAt(tx, ty) {
      if (tx < 0 || ty < 0 || tx >= tileWidth || ty >= tileHeight) {
        throw new Error(`tile (${tx},${ty}) outside ${tileWidth}×${tileHeight}`);
      }
      return buf.readUInt16LE(32 + 2 * (ty * tileWidth + tx));
    },
  };
}

/** Run the real published Tiler on a synthesized terrain grid; return the parsed tile grid. */
export function runTilerProbe({ width, height, terrain }) {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "legacy-tiler-probe-"));
  try {
    const jobId = "probe";
    const input = path.join(workDir, `${jobId}.heightmap`);
    fs.writeFileSync(input, writeHeightmapBuffer(width, height, terrain));
    execFileSync(TILER_BINARY, [input], { cwd: workDir, timeout: 60_000, stdio: "pipe" });
    return parseMapTiles(fs.readFileSync(path.join(workDir, "outbox", `${jobId}.maptiles`)));
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}
