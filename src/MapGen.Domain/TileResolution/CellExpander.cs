namespace MapGen.Domain.TileResolution;

/// <summary>
/// The cell-to-tile expansion rule — the production twin of the verified model
/// (specs/tiling/CellToTile.dfy ExpandCell). Pure and deterministic: no clock, no
/// randomness, no IO. Postconditions (exactly four, unique, in-bounds, exact corners)
/// are proved in Dafny and mirrored by FsCheck properties in MapGen.Domain.Tests.
/// </summary>
public static class CellExpander
{
    /// <summary>
    /// Expand <paramref name="cell"/> into its 2×2 tile region.
    /// Precondition: the cell lies inside <paramref name="dimensions"/>.
    /// </summary>
    public static TileRegion Expand(CellCoordinate cell, CellMapDimensions dimensions)
    {
        if (!dimensions.Contains(cell))
        {
            throw new ArgumentOutOfRangeException(
                nameof(cell),
                cell,
                $"Cell ({cell.X},{cell.Y}) is outside the {dimensions.Width}×{dimensions.Height} cell map.");
        }

        int baseX = cell.X * 2;
        int baseY = cell.Y * 2;

        return new TileRegion(
            topLeft: new TileCoordinate(baseX, baseY),
            topRight: new TileCoordinate(baseX + 1, baseY),
            bottomLeft: new TileCoordinate(baseX, baseY + 1),
            bottomRight: new TileCoordinate(baseX + 1, baseY + 1));
    }
}
