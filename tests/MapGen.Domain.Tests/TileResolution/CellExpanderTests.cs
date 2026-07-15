using MapGen.Domain.TileResolution;
using Xunit;

namespace MapGen.Domain.Tests.TileResolution;

/// <summary>
/// Charter unit cases (mapgen-spec-driven-planning/08, Test Plan): origin, interior,
/// final valid cell, and every rejection edge. Property tests carry the general laws.
/// </summary>
public class CellExpanderTests
{
    private static readonly CellMapDimensions TenByTen = new(10, 10);

    [Fact]
    public void Origin_cell_expands_to_its_corner_region_in_contractual_order()
    {
        var region = CellExpander.Expand(new CellCoordinate(0, 0), TenByTen);

        Assert.Equal(new TileCoordinate(0, 0), region.TopLeft);
        Assert.Equal(new TileCoordinate(1, 0), region.TopRight);
        Assert.Equal(new TileCoordinate(0, 1), region.BottomLeft);
        Assert.Equal(new TileCoordinate(1, 1), region.BottomRight);
    }

    [Fact]
    public void Interior_cell_3_4_expands_to_6_8_through_7_9()
    {
        var region = CellExpander.Expand(new CellCoordinate(3, 4), TenByTen);

        Assert.Equal(new TileCoordinate(6, 8), region.TopLeft);
        Assert.Equal(new TileCoordinate(7, 8), region.TopRight);
        Assert.Equal(new TileCoordinate(6, 9), region.BottomLeft);
        Assert.Equal(new TileCoordinate(7, 9), region.BottomRight);
    }

    [Fact]
    public void Final_valid_cell_stays_inside_the_doubled_tile_map()
    {
        var region = CellExpander.Expand(new CellCoordinate(9, 9), TenByTen);
        var tileMap = TileMapDimensions.From(TenByTen);

        Assert.All(region.Coordinates, t => Assert.True(tileMap.Contains(t)));
        Assert.Equal(new TileCoordinate(19, 19), region.BottomRight);
    }

    [Theory]
    [InlineData(10, 9)] // x == width
    [InlineData(9, 10)] // y == height
    public void Cell_on_or_past_the_boundary_is_rejected(int x, int y)
    {
        Assert.Throws<ArgumentOutOfRangeException>(
            () => CellExpander.Expand(new CellCoordinate(x, y), TenByTen));
    }

    [Theory]
    [InlineData(-1, 0)]
    [InlineData(0, -1)]
    public void Negative_coordinates_cannot_be_constructed(int x, int y)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => new CellCoordinate(x, y));
    }

    [Theory]
    [InlineData(0, 10)]
    [InlineData(10, 0)]
    [InlineData(-5, 10)]
    public void Non_positive_dimensions_cannot_be_constructed(int width, int height)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => new CellMapDimensions(width, height));
    }
}
