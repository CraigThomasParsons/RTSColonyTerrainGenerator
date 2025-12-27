using System;
using Tiler.Model;

namespace Tiler.Processing
{
    /// <summary>
    /// Resolves final tile IDs from authoritative cell data.
    ///
    /// This class converts:
    ///   - Cell terrain layers
    ///   - Cell adjacency bitmasks
    ///
    /// Into:
    ///   - A fully resolved tile ID grid
    ///
    /// Each cell produces exactly four tiles (2×2),
    /// and all four tiles receive the same tile ID.
    ///
    /// This stage performs NO procedural logic and NO refinement.
    /// It is a direct, deterministic mapping.
    /// </summary>
    public static class TileIdResolver
    {
        /// <summary>
        /// Resolves a tile ID grid from cell terrain layers and adjacency masks.
        ///
        /// Output grid dimensions:
        ///   tileWidth  = cellWidth  * 2
        ///   tileHeight = cellHeight * 2
        ///
        /// Coordinate convention:
        /// - Tile (0,0) is top-left
        /// - x increases right
        /// - y increases down
        /// </summary>
        /// <param name="heightmap">
        /// HeightmapData containing authoritative terrain layers.
        /// </param>
        /// <param name="cellMasks">
        /// 4-bit adjacency masks indexed as [cellX, cellY].
        /// </param>
        /// <returns>
        /// A 2D array of resolved tile IDs indexed as [tileX, tileY].
        /// </returns>
        public static ushort[,] Resolve(
            HeightmapData heightmap,
            byte[,] cellMasks)
        {
            if (heightmap == null)
                throw new ArgumentNullException(nameof(heightmap));

            if (cellMasks == null)
                throw new ArgumentNullException(nameof(cellMasks));

            uint cellWidth = heightmap.WidthInCells;
            uint cellHeight = heightmap.HeightInCells;

            if (cellMasks.GetLength(0) != cellWidth ||
                cellMasks.GetLength(1) != cellHeight)
            {
                throw new ArgumentException(
                    "Cell mask dimensions must match heightmap dimensions.");
            }

            uint tileWidth = cellWidth * 2;
            uint tileHeight = cellHeight * 2;

            ushort[,] tileIds = new ushort[tileWidth, tileHeight];

            // ---- Resolve per cell ----
            // Iterate in deterministic row-major order
            for (uint cellY = 0; cellY < cellHeight; cellY++)
            {
                for (uint cellX = 0; cellX < cellWidth; cellX++)
                {
                    // Terrain layer occupies the high byte
                    ushort terrainBits = (ushort)((byte)heightmap.TerrainLayers[cellX, cellY] << 8);

                    // Mask occupies the low nibble
                    ushort maskBits = cellMasks[cellX, cellY];

                    // Final tile ID
                    ushort tileId = (ushort)(terrainBits | maskBits);

                    // ---- Emit 2×2 tiles ----
                    // Cell (cellX, cellY) maps to tiles:
                    //   (2x,2y), (2x+1,2y)
                    //   (2x,2y+1), (2x+1,2y+1)

                    uint tileBaseX = cellX * 2;
                    uint tileBaseY = cellY * 2;

                    tileIds[tileBaseX,     tileBaseY    ] = tileId; // TL
                    tileIds[tileBaseX + 1, tileBaseY    ] = tileId; // TR
                    tileIds[tileBaseX,     tileBaseY + 1] = tileId; // BL
                    tileIds[tileBaseX + 1, tileBaseY + 1] = tileId; // BR
                }
            }

            return tileIds;
        }
    }
}
