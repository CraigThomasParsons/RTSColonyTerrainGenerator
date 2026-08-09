using System.Text.Json;
using MapGen.Domain.TileResolution;
using Xunit;

namespace MapGen.CompatibilityTests;

/// <summary>
/// Slice-01 compatibility evidence: the legacy Tiler's real production artifacts obey
/// the dimension-doubling law the verified model proves (CellToTile.dfy TileMapWidth/
/// Height) and the C# domain implements (TileMapDimensions.From). Each golden job's
/// input declared its cell dimensions; the .maptiles the legacy pipeline actually
/// produced must be exactly double, and the domain must agree.
/// </summary>
public class GoldenTilerDimensionsTest
{
    [Theory]
    [InlineData("43860dcf-6469-42a7-9843-4e33abeacfac")]
    [InlineData("3c96b74c-6f86-4d27-a0ca-c567f385ae8e")]
    [InlineData("0860a05a-a410-4cc2-987d-a48a4cd120c7")]
    public void Golden_maptiles_dimensions_are_exactly_double_the_input_cell_dimensions(string job)
    {
        using var spec = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(GoldenFixtures.JobDir(job), "input.job.json")));
        int cellWidth = spec.RootElement.GetProperty("map_width_in_cells").GetInt32();
        int cellHeight = spec.RootElement.GetProperty("map_height_in_cells").GetInt32();

        byte[] maptiles = File.ReadAllBytes(GoldenFixtures.ArtifactPath(job, ".maptiles"));
        Assert.Equal("MTIL", System.Text.Encoding.ASCII.GetString(maptiles, 0, 4));
        int tileWidth = BitConverter.ToInt32(maptiles, 8);
        int tileHeight = BitConverter.ToInt32(maptiles, 12);

        // The legacy pipeline's behaviour, recorded in production artifacts:
        Assert.Equal(cellWidth * 2, tileWidth);
        Assert.Equal(cellHeight * 2, tileHeight);

        // And the new domain agrees with the legacy baseline:
        var domain = TileMapDimensions.From(new CellMapDimensions(cellWidth, cellHeight));
        Assert.Equal(tileWidth, domain.Width);
        Assert.Equal(tileHeight, domain.Height);
    }
}
