namespace MapGen.Domain.TileResolution;

/// <summary>
/// Zero-based (x, y) position in tile space — the grid twice the cell dimensions
/// in each axis (mirrors TileCoordinate in specs/tiling/CellToTile.dfy).
/// </summary>
public readonly record struct TileCoordinate
{
    public int X { get; }
    public int Y { get; }

    public TileCoordinate(int x, int y)
    {
        if (x < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(x), x, "Tile x must not be negative.");
        }

        if (y < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(y), y, "Tile y must not be negative.");
        }

        X = x;
        Y = y;
    }
}
