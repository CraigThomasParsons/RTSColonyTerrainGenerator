using System;
using System.IO;

namespace Tiler.IO
{
    /// <summary>
    /// Writes resolved tile data to a .maptiles binary artifact.
    ///
    /// This file is the FINAL output of the Tiler stage.
    /// It contains fully resolved tile IDs and requires no
    /// post-processing by the game engine.
    ///
    /// Binary format (little-endian):
    ///
    /// Header (32 bytes):
    ///   char[4]  magic           ("MTIL")
    ///   u32      version         (currently 1)
    ///   u32      tile_width
    ///   u32      tile_height
    ///   u64      deterministic_seed
    ///   u32      tile_count
    ///   u32      reserved        (must be 0)
    ///
    /// Body:
    ///   u16[tile_count] tile_ids (row-major)
    /// </summary>
    public static class MapTilesWriter
    {
        /// <summary>
        /// Writes a .maptiles file to disk.
        ///
        /// Determinism:
        /// - Given the same tile IDs and metadata, output bytes
        ///   are identical on every run.
        /// </summary>
        /// <param name="outputPath">Destination file path.</param>
        /// <param name="tileIds">
        /// Fully resolved tile ID grid indexed as [x, y].
        /// </param>
        /// <param name="deterministicSeed">
        /// Seed copied from the heightmap for provenance.
        /// </param>
        public static void Write(
            string outputPath,
            ushort[,] tileIds,
            ulong deterministicSeed)
        {
            if (tileIds == null)
                throw new ArgumentNullException(nameof(tileIds));

            uint tileWidth = (uint)tileIds.GetLength(0);
            uint tileHeight = (uint)tileIds.GetLength(1);

            if (tileWidth == 0 || tileHeight == 0)
                throw new ArgumentException("Tile grid must be non-empty.");

            uint tileCount = tileWidth * tileHeight;

            using FileStream stream = File.Create(outputPath);
            using BinaryWriter writer = new BinaryWriter(stream);

            // ---- Header ----

            // Magic: "MTIL"
            writer.Write(new[] { (byte)'M', (byte)'T', (byte)'I', (byte)'L' });

            // Version
            writer.Write((uint)1);

            // Dimensions
            writer.Write(tileWidth);
            writer.Write(tileHeight);

            // Deterministic seed
            writer.Write(deterministicSeed);

            // Tile count
            writer.Write(tileCount);

            // Reserved (must be zero)
            writer.Write((uint)0);

            // ---- Tile IDs (row-major) ----
            for (uint y = 0; y < tileHeight; y++)
            {
                for (uint x = 0; x < tileWidth; x++)
                {
                    writer.Write(tileIds[x, y]);
                }
            }
        }
    }
}
