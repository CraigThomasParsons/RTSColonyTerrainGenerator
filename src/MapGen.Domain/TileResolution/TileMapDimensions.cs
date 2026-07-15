namespace MapGen.Domain.TileResolution;

/// <summary>
/// Width and height of the expanded map, measured in tiles. Only derivable from
/// cell dimensions — exactly double in each axis (CellToTile.dfy TileMapWidth/Height),
/// which is what the legacy Tiler produces (TileIdResolver.cs).
/// </summary>
public sealed record TileMapDimensions
{
    public int Width { get; }
    public int Height { get; }

    private TileMapDimensions(int width, int height)
    {
        Width = width;
        Height = height;
    }

    public static TileMapDimensions From(CellMapDimensions cells)
        => new(cells.Width * 2, cells.Height * 2);

    public bool Contains(TileCoordinate tile) => tile.X < Width && tile.Y < Height;
}
