using FsCheck;
using FsCheck.Fluent;
using FsCheck.Xunit;
using MapGen.Domain.TileResolution;

namespace MapGen.Domain.Tests.TileResolution;

/// <summary>
/// FsCheck twins of the Dafny lemmas in specs/tiling/CellToTile.dfy — every property
/// here names the lemma it mirrors. The verified model proves the law; these check the
/// production implementation obeys the same law over generated inputs.
/// </summary>
public class CellExpanderPropertyTests
{
    /// <summary>Valid (dimensions, in-bounds cell) pairs.</summary>
    private static Arbitrary<(CellMapDimensions Dims, CellCoordinate Cell)> ValidInputs()
        => (from width in Gen.Choose(1, 256)
            from height in Gen.Choose(1, 256)
            from x in Gen.Choose(0, width - 1)
            from y in Gen.Choose(0, height - 1)
            select (new CellMapDimensions(width, height), new CellCoordinate(x, y)))
           .ToArbitrary();

    [Property(MaxTest = 500)]
    public Property Region_has_exactly_four_coordinates() // ExpandCellProducesExactlyFour
        => Prop.ForAll(ValidInputs(), input =>
            CellExpander.Expand(input.Cell, input.Dims).Coordinates.Count == 4);

    [Property(MaxTest = 500)]
    public Property Coordinates_are_all_distinct() // ExpandCellCoordinatesAreUnique
        => Prop.ForAll(ValidInputs(), input =>
            CellExpander.Expand(input.Cell, input.Dims).Coordinates.Distinct().Count() == 4);

    [Property(MaxTest = 500)]
    public Property Every_coordinate_is_inside_the_doubled_tile_map() // ExpandCellStaysInTileBounds
        => Prop.ForAll(ValidInputs(), input =>
        {
            var tileMap = TileMapDimensions.From(input.Dims);
            return CellExpander.Expand(input.Cell, input.Dims).Coordinates.All(tileMap.Contains);
        });

    [Property(MaxTest = 500)]
    public Property Extrema_are_2x_2y_through_2x_plus_1_2y_plus_1() // ExpandCellExtrema
        => Prop.ForAll(ValidInputs(), input =>
        {
            var tiles = CellExpander.Expand(input.Cell, input.Dims).Coordinates;
            return tiles.Min(t => t.X) == input.Cell.X * 2
                && tiles.Max(t => t.X) == input.Cell.X * 2 + 1
                && tiles.Min(t => t.Y) == input.Cell.Y * 2
                && tiles.Max(t => t.Y) == input.Cell.Y * 2 + 1;
        });

    [Property(MaxTest = 500)]
    public Property Expansion_is_deterministic() // structural in Dafny (pure function)
        => Prop.ForAll(ValidInputs(), input =>
            CellExpander.Expand(input.Cell, input.Dims)
                .Equals(CellExpander.Expand(input.Cell, input.Dims)));

    [Property(MaxTest = 500)]
    public Property Distinct_cells_have_disjoint_regions() // DistinctCellsHaveDisjointRegions
        => Prop.ForAll(ValidInputs(), input =>
        {
            var other = new CellCoordinate(
                (input.Cell.X + 1) % input.Dims.Width,
                input.Cell.Y);
            if (other == input.Cell)
            {
                return true; // 1-wide map: no distinct sibling on this axis
            }

            var a = CellExpander.Expand(input.Cell, input.Dims).Coordinates;
            var b = CellExpander.Expand(other, input.Dims).Coordinates;
            return !a.Intersect(b).Any();
        });
}
