namespace MapGen.Domain.TileResolution;

/// <summary>
/// Zero-based (x, y) position in cell space. Coordinates are never negative;
/// upper bounds belong to <see cref="CellMapDimensions"/>, not the coordinate itself.
/// </summary>
public readonly record struct CellCoordinate
{
    public int X { get; }
    public int Y { get; }

    public CellCoordinate(int x, int y)
    {
        if (x < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(x), x, "Cell x must not be negative.");
        }

        if (y < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(y), y, "Cell y must not be negative.");
        }

        X = x;
        Y = y;
    }
}
