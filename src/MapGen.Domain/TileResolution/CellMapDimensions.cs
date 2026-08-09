namespace MapGen.Domain.TileResolution;

/// <summary>
/// Width and height of the source map, measured in cells. Both are strictly positive
/// (precondition of the verified model, CellToTile.dfy ValidDimensions).
/// </summary>
public sealed record CellMapDimensions
{
    public int Width { get; }
    public int Height { get; }

    public CellMapDimensions(int width, int height)
    {
        if (width <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(width), width, "Cell map width must be greater than zero.");
        }

        if (height <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(height), height, "Cell map height must be greater than zero.");
        }

        Width = width;
        Height = height;
    }

    public bool Contains(CellCoordinate cell) => cell.X < Width && cell.Y < Height;
}
