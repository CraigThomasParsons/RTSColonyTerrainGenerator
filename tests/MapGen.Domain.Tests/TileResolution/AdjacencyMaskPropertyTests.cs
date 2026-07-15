using FsCheck;
using FsCheck.Fluent;
using FsCheck.Xunit;
using MapGen.Domain.TileResolution;

namespace MapGen.Domain.Tests.TileResolution;

/// <summary>
/// FsCheck twins of the lemmas in specs/tiling/AdjacencyMask.dfy — each property names
/// the lemma it mirrors. The verified model proves the law; these check the production
/// implementation obeys it over generated grids.
/// </summary>
public class AdjacencyMaskPropertyTests
{
    /// <summary>A random small grid (terrain values 0..3 to match the legacy range) plus an in-bounds cell.</summary>
    private static Arbitrary<(TerrainGrid Grid, int X, int Y)> GridAndCell()
        => (from width in Gen.Choose(1, 12)
            from height in Gen.Choose(1, 12)
            from terrain in Gen.Choose(0, 3).ArrayOf(width * height)
            from x in Gen.Choose(0, width - 1)
            from y in Gen.Choose(0, height - 1)
            select (new TerrainGrid(width, height, terrain), x, y))
           .ToArbitrary();

    [Property(MaxTest = 500)]
    public Property Mask_is_always_in_range_0_to_15() // MaskInRange
        => Prop.ForAll(GridAndCell(), input =>
        {
            int v = AdjacencyMaskCalculator.ComputeMask(input.Grid, input.X, input.Y).Value;
            return v is >= 0 and <= 15;
        });

    [Property(MaxTest = 500)]
    public Property Edge_cells_never_set_off_map_bits() // EdgeCellsNeverSetOffMapBits
        => Prop.ForAll(GridAndCell(), input =>
        {
            var (grid, x, y) = input;
            var mask = AdjacencyMaskCalculator.ComputeMask(grid, x, y);
            return (y != 0 || !mask.HasNorth)
                && (x != 0 || !mask.HasWest)
                && (y != grid.Height - 1 || !mask.HasSouth)
                && (x != grid.Width - 1 || !mask.HasEast);
        });

    [Property(MaxTest = 500)]
    public Property Each_bit_reflects_its_neighbour_predicate() // BitsReflectNeighbourPredicate
        => Prop.ForAll(GridAndCell(), input =>
        {
            var (grid, x, y) = input;
            var mask = AdjacencyMaskCalculator.ComputeMask(grid, x, y);
            int self = grid.TerrainAt(x, y);
            bool north = y > 0 && grid.TerrainAt(x, y - 1) == self;
            bool east = x + 1 < grid.Width && grid.TerrainAt(x + 1, y) == self;
            bool south = y + 1 < grid.Height && grid.TerrainAt(x, y + 1) == self;
            bool west = x > 0 && grid.TerrainAt(x - 1, y) == self;
            return mask.HasNorth == north && mask.HasEast == east
                && mask.HasSouth == south && mask.HasWest == west;
        });

    [Property(MaxTest = 500)]
    public Property East_west_symmetry_holds() // EastWestSymmetry
        => Prop.ForAll(GridAndCell(), input =>
        {
            var (grid, x, y) = input;
            if (x + 1 >= grid.Width)
            {
                return true; // no east neighbour to be symmetric with
            }
            bool selfEast = AdjacencyMaskCalculator.ComputeMask(grid, x, y).HasEast;
            bool neighbourWest = AdjacencyMaskCalculator.ComputeMask(grid, x + 1, y).HasWest;
            return selfEast == neighbourWest;
        });

    [Property(MaxTest = 500)]
    public Property North_south_symmetry_holds() // NorthSouthSymmetry
        => Prop.ForAll(GridAndCell(), input =>
        {
            var (grid, x, y) = input;
            if (y + 1 >= grid.Height)
            {
                return true;
            }
            bool selfSouth = AdjacencyMaskCalculator.ComputeMask(grid, x, y).HasSouth;
            bool neighbourNorth = AdjacencyMaskCalculator.ComputeMask(grid, x, y + 1).HasNorth;
            return selfSouth == neighbourNorth;
        });

    [Property(MaxTest = 500)]
    public Property Computation_is_deterministic()
        => Prop.ForAll(GridAndCell(), input =>
            AdjacencyMaskCalculator.ComputeMask(input.Grid, input.X, input.Y).Value
                == AdjacencyMaskCalculator.ComputeMask(input.Grid, input.X, input.Y).Value);
}
