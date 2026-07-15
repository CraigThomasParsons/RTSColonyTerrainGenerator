using System.Collections.ObjectModel;

namespace MapGen.Domain.TileResolution;

/// <summary>
/// The four tiles belonging to one cell, in the contractual order TL, TR, BL, BR
/// (CellToTile.dfy ExpandCellEmitsTheContractualCorners; legacy TileIdResolver.cs
/// emits the same order). Constructed only by <see cref="CellExpander"/>.
/// </summary>
public sealed record TileRegion
{
    public ReadOnlyCollection<TileCoordinate> Coordinates { get; }

    public TileCoordinate TopLeft => Coordinates[0];
    public TileCoordinate TopRight => Coordinates[1];
    public TileCoordinate BottomLeft => Coordinates[2];
    public TileCoordinate BottomRight => Coordinates[3];

    internal TileRegion(TileCoordinate topLeft, TileCoordinate topRight, TileCoordinate bottomLeft, TileCoordinate bottomRight)
    {
        var coordinates = new[] { topLeft, topRight, bottomLeft, bottomRight };
        if (coordinates.Distinct().Count() != 4)
        {
            throw new ArgumentException("A tile region must contain four unique coordinates.");
        }

        Coordinates = Array.AsReadOnly(coordinates);
    }

    // Value semantics over the ordered coordinates. The default record equality would
    // compare the ReadOnlyCollection reference — two identical expansions would differ.
    // Caught by CellExpanderPropertyTests.Expansion_is_deterministic.
    public bool Equals(TileRegion? other)
        => other is not null && Coordinates.SequenceEqual(other.Coordinates);

    public override int GetHashCode()
        => HashCode.Combine(TopLeft, TopRight, BottomLeft, BottomRight);
}
