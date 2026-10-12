namespace MapGen.Contracts.Tiles;

/// <summary>A tile-space coordinate on the wire.</summary>
public sealed record TilePosition(int X, int Y);

/// <summary>
/// The 2×2 tile region of one cell. <see cref="Tiles"/> is ordered TL, TR, BL, BR — the
/// contractual order <c>TileRegion</c> documents and <c>CellToTile.dfy</c> proves. Clients
/// must not re-sort it.
///
/// Not a new shape: <c>MapGen.Cli expand-cell</c> already prints exactly this. It exists
/// only because a <c>Result&lt;TileRegion&gt;</c> is not itself serialisable at a wire
/// boundary.
/// </summary>
public sealed record TileRegionResponse(TilePosition Cell, IReadOnlyList<TilePosition> Tiles);

/// <summary>
/// The 4-bit adjacency mask of one cell. <see cref="Mask"/> is the raw 0–15 byte; the four
/// booleans are derived (N=1, E=2, S=4, W=8) and sent for readability, not as independent
/// truth. Mirrors <c>MapGen.Cli mask-cell</c> field for field.
/// </summary>
public sealed record AdjacencyMaskResponse(
    TilePosition Cell,
    int Mask,
    bool North,
    bool East,
    bool South,
    bool West);
