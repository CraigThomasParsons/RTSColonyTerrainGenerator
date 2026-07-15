namespace MapGen.Domain.TileResolution;

/// <summary>
/// A 4-bit orthogonal adjacency mask for one cell (mirrors Mask in
/// specs/tiling/AdjacencyMask.dfy). A direction bit is set iff that neighbour exists and
/// shares the cell's terrain. Value is always in [0, 15].
///
///   North = 1, East = 2, South = 4, West = 8.
/// </summary>
public readonly record struct AdjacencyMask
{
    public const int North = 1;
    public const int East = 2;
    public const int South = 4;
    public const int West = 8;

    public byte Value { get; }

    public AdjacencyMask(int value)
    {
        if (value is < 0 or > 15)
        {
            throw new ArgumentOutOfRangeException(nameof(value), value, "An adjacency mask must be in [0, 15].");
        }

        Value = (byte)value;
    }

    public bool HasNorth => (Value & North) != 0;
    public bool HasEast => (Value & East) != 0;
    public bool HasSouth => (Value & South) != 0;
    public bool HasWest => (Value & West) != 0;
}
