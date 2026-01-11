using System;
using Tiler.Model;

namespace Tiler.Processing
{
    /// <summary>
    /// Computes deterministic 4-bit adjacency masks for each cell
    /// in a heightmap based on terrain layer equality.
    ///
    /// This class is PURE:
    /// - No randomness
    /// - No mutation of input
    /// - No I/O
    ///
    /// It implements the locked bitmasking contract:
    ///
    ///   Bit 0 (1) = North
    ///   Bit 1 (2) = East
    ///   Bit 2 (4) = South
    ///   Bit 3 (8) = West
    ///
    /// A bit is set if and only if the neighboring cell exists
    /// AND has the same TerrainLayer as the current cell.
    ///
    /// Diagonals are intentionally ignored at this stage.
    /// </summary>
    public static class CellBitmaskCalculator
    {
        /// <summary>
        /// Computes a 4-bit adjacency mask for every cell in the heightmap.
        ///
        /// The returned array has the same dimensions as the cell grid:
        ///   mask[x, y] ∈ [0..15]
        ///
        /// Coordinate convention:
        /// - (0,0) is top-left
        /// - x increases right
        /// - y increases down
        ///
        /// Determinism guarantee:
        /// - For identical HeightmapData input, output masks are byte-for-byte identical.
        /// </summary>
        /// <param name="heightmap">
        /// Fully validated HeightmapData produced by HeightmapReader.
        /// </param>
        /// <returns>
        /// A 2D byte array of size [width, height] containing bitmasks.
        /// </returns>
        public static byte[,] ComputeMasks(HeightmapData heightmap)
        {
            if (heightmap == null)
                throw new ArgumentNullException(nameof(heightmap));

            uint width = heightmap.WidthInCells;
            uint height = heightmap.HeightInCells;

            byte[,] masks = new byte[width, height];

            // Iterate over every cell in deterministic order (row-major)
            for (uint y = 0; y < height; y++)
            {
                for (uint x = 0; x < width; x++)
                {
                    masks[x, y] = ComputeMaskForCell(heightmap, x, y);
                }
            }

            return masks;
        }

        /// <summary>
        /// Computes the 4-bit adjacency mask for a single cell.
        ///
        /// This method contains the complete and authoritative definition
        /// of how adjacency is evaluated.
        /// </summary>
        /// <param name="heightmap">Source heightmap data.</param>
        /// <param name="x">Cell X coordinate.</param>
        /// <param name="y">Cell Y coordinate.</param>
        /// <returns>4-bit mask in the range [0..15].</returns>
        private static byte ComputeMaskForCell(
            HeightmapData heightmap,
            uint x,
            uint y)
        {
            TerrainLayer self = heightmap.TerrainLayers[x, y];

            byte mask = 0;

            // ---- North (bit 0) ----
            if (y > 0)
            {
                if (heightmap.TerrainLayers[x, y - 1] == self)
                {
                    mask |= 1; // 0001
                }
            }

            // ---- East (bit 1) ----
            if (x + 1 < heightmap.WidthInCells)
            {
                if (heightmap.TerrainLayers[x + 1, y] == self)
                {
                    mask |= 2; // 0010
                }
            }

            // ---- South (bit 2) ----
            if (y + 1 < heightmap.HeightInCells)
            {
                if (heightmap.TerrainLayers[x, y + 1] == self)
                {
                    mask |= 4; // 0100
                }
            }

            // ---- West (bit 3) ----
            if (x > 0)
            {
                if (heightmap.TerrainLayers[x - 1, y] == self)
                {
                    mask |= 8; // 1000
                }
            }

            return mask;
        }
    }
}
