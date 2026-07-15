namespace MapGen.Domain.TileResolution;

/// <summary>
/// A width×height grid of terrain values in row-major order — the input to adjacency-mask
/// construction (mirrors Grid in specs/tiling/AdjacencyMask.dfy). Terrain values are the
/// cell's terrain layer; equality of two cells' values is what "same terrain" means.
/// </summary>
public sealed class TerrainGrid
{
    private readonly int[] _terrain;

    public int Width { get; }
    public int Height { get; }

    /// <param name="terrain">Row-major, length width*height: index = y*width + x.</param>
    public TerrainGrid(int width, int height, IReadOnlyList<int> terrain)
    {
        if (width <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(width), width, "Grid width must be greater than zero.");
        }

        if (height <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(height), height, "Grid height must be greater than zero.");
        }

        if (terrain.Count != width * height)
        {
            throw new ArgumentException(
                $"Terrain length {terrain.Count} does not match {width}×{height} = {width * height}.",
                nameof(terrain));
        }

        Width = width;
        Height = height;
        _terrain = terrain.ToArray();
    }

    public int TerrainAt(int x, int y) => _terrain[(y * Width) + x];

    public bool Contains(int x, int y) => x >= 0 && y >= 0 && x < Width && y < Height;
}
