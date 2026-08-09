namespace MapGen.Domain.TileResolution;

/// <summary>
/// Adjacency-mask construction — the production twin of the verified model
/// (specs/tiling/AdjacencyMask.dfy Mask). Pure and deterministic: a direction bit is set
/// iff that orthogonal neighbour exists on the grid and shares the cell's terrain.
/// Diagonals ignored. Postconditions (range, per-bit predicate, edge safety, symmetry)
/// are proved in Dafny and mirrored by FsCheck properties.
/// </summary>
public static class AdjacencyMaskCalculator
{
    /// <summary>Compute the 4-bit mask for one in-bounds cell.</summary>
    public static AdjacencyMask ComputeMask(TerrainGrid grid, int x, int y)
    {
        if (!grid.Contains(x, y))
        {
            throw new ArgumentOutOfRangeException(
                nameof(x),
                $"Cell ({x},{y}) is outside the {grid.Width}×{grid.Height} terrain grid.");
        }

        int self = grid.TerrainAt(x, y);
        int mask = 0;

        if (y > 0 && grid.TerrainAt(x, y - 1) == self)
        {
            mask |= AdjacencyMask.North;
        }

        if (x + 1 < grid.Width && grid.TerrainAt(x + 1, y) == self)
        {
            mask |= AdjacencyMask.East;
        }

        if (y + 1 < grid.Height && grid.TerrainAt(x, y + 1) == self)
        {
            mask |= AdjacencyMask.South;
        }

        if (x > 0 && grid.TerrainAt(x - 1, y) == self)
        {
            mask |= AdjacencyMask.West;
        }

        return new AdjacencyMask(mask);
    }
}
