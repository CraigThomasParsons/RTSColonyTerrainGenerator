using MapGen.Domain.TileResolution;
using Xunit;

namespace MapGen.Domain.Tests.TileResolution;

/// <summary>
/// Charter example cases for adjacency-mask construction. Property tests carry the
/// general laws (range, per-bit predicate, edge safety, symmetry).
/// </summary>
public class AdjacencyMaskCalculatorTests
{
    // A 3×3 grid, row-major.
    private static TerrainGrid Grid3x3(params int[] terrain) => new(3, 3, terrain);

    [Fact]
    public void Interior_cell_surrounded_by_same_terrain_sets_all_four_bits()
    {
        var mask = AdjacencyMaskCalculator.ComputeMask(Grid3x3(1, 1, 1, 1, 1, 1, 1, 1, 1), 1, 1);

        Assert.Equal(15, mask.Value);
        Assert.True(mask is { HasNorth: true, HasEast: true, HasSouth: true, HasWest: true });
    }

    [Fact]
    public void Corner_cell_can_only_set_east_and_south()
    {
        var mask = AdjacencyMaskCalculator.ComputeMask(Grid3x3(1, 1, 1, 1, 1, 1, 1, 1, 1), 0, 0);

        Assert.Equal(AdjacencyMask.East | AdjacencyMask.South, mask.Value); // 6
        Assert.False(mask.HasNorth);
        Assert.False(mask.HasWest);
    }

    [Fact]
    public void Cell_whose_neighbours_all_differ_sets_no_bits()
    {
        // centre = 3, all four orthogonal neighbours = 2
        var mask = AdjacencyMaskCalculator.ComputeMask(Grid3x3(1, 2, 1, 2, 3, 2, 1, 2, 1), 1, 1);

        Assert.Equal(0, mask.Value);
    }

    [Fact]
    public void Only_matching_neighbours_set_their_bit()
    {
        // centre = 1; North=1 (match), East=2, South=1 (match), West=2
        var mask = AdjacencyMaskCalculator.ComputeMask(Grid3x3(9, 1, 9, 2, 1, 2, 9, 1, 9), 1, 1);

        Assert.True(mask.HasNorth);
        Assert.False(mask.HasEast);
        Assert.True(mask.HasSouth);
        Assert.False(mask.HasWest);
        Assert.Equal(AdjacencyMask.North | AdjacencyMask.South, mask.Value); // 5
    }

    [Theory]
    [InlineData(3, 1)] // x == width
    [InlineData(1, 3)] // y == height
    public void Out_of_bounds_cell_is_rejected(int x, int y)
    {
        var grid = Grid3x3(1, 1, 1, 1, 1, 1, 1, 1, 1);
        Assert.Throws<ArgumentOutOfRangeException>(() => AdjacencyMaskCalculator.ComputeMask(grid, x, y));
    }

    [Fact]
    public void Terrain_length_must_match_dimensions()
    {
        Assert.Throws<ArgumentException>(() => new TerrainGrid(3, 3, new[] { 1, 1, 1 }));
    }
}
