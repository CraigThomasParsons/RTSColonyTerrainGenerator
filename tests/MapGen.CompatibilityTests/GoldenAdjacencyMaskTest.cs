using MapGen.Domain.TileResolution;
using Xunit;

namespace MapGen.CompatibilityTests;

/// <summary>
/// Slice-02 compatibility evidence against real production artifacts: recompute the
/// adjacency mask from each golden job's input .heightmap with the new domain code, and
/// confirm it matches the mask the legacy pipeline actually baked into the golden
/// .maptiles (the tile-id low nibble). This checks the new implementation reproduces the
/// legacy behaviour on real terrain, not just synthetic BDD grids.
/// </summary>
public class GoldenAdjacencyMaskTest
{
    [Theory]
    [InlineData("43860dcf-6469-42a7-9843-4e33abeacfac")]
    [InlineData("3c96b74c-6f86-4d27-a0ca-c567f385ae8e")]
    [InlineData("0860a05a-a410-4cc2-987d-a48a4cd120c7")]
    public void New_masks_match_the_legacy_maptiles_low_nibble(string job)
    {
        var (grid, cellWidth, cellHeight) = ReadHeightmapTerrain(GoldenFixtures.ArtifactPath(job, ".heightmap"));
        ushort[] tileIds = ReadMapTiles(GoldenFixtures.ArtifactPath(job, ".maptiles"), out int tileWidth);

        // Spot-check a spread of cells (checking all 4096 would be fine too, but this keeps
        // the failure message small while still covering interior, edges, and corners).
        foreach (var (x, y) in SampleCells(cellWidth, cellHeight))
        {
            int expected = AdjacencyMaskCalculator.ComputeMask(grid, x, y).Value;
            int legacyNibble = tileIds[(2 * y * tileWidth) + (2 * x)] & 0x0F; // cell (x,y) owns tile (2x,2y)
            Assert.True(expected == legacyNibble,
                $"job {job} cell ({x},{y}): new mask {expected} != legacy nibble {legacyNibble}");
        }
    }

    private static IEnumerable<(int X, int Y)> SampleCells(int width, int height)
    {
        (int, int)[] corners = { (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1) };
        foreach (var c in corners)
        {
            yield return c;
        }
        for (int y = 0; y < height; y += 7)
        {
            for (int x = 0; x < width; x += 7)
            {
                yield return (x, y);
            }
        }
    }

    private static (TerrainGrid Grid, int Width, int Height) ReadHeightmapTerrain(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        int width = BitConverter.ToInt32(bytes, 0);
        int height = BitConverter.ToInt32(bytes, 4);
        int n = width * height;
        // layout: 16-byte header, u8 heights[n], u8 terrain[n]
        var terrain = new int[n];
        for (int i = 0; i < n; i++)
        {
            terrain[i] = bytes[16 + n + i];
        }
        return (new TerrainGrid(width, height, terrain), width, height);
    }

    private static ushort[] ReadMapTiles(string path, out int tileWidth)
    {
        byte[] bytes = File.ReadAllBytes(path);
        tileWidth = BitConverter.ToInt32(bytes, 8);
        int tileHeight = BitConverter.ToInt32(bytes, 12);
        int count = tileWidth * tileHeight;
        var ids = new ushort[count];
        for (int i = 0; i < count; i++)
        {
            ids[i] = BitConverter.ToUInt16(bytes, 32 + (2 * i));
        }
        return ids;
    }
}
