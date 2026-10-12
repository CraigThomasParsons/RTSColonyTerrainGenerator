namespace MapGen.Application.WorldGeneration;

/// <summary>
/// The artifacts of one completed golden job, already parsed out of their on-disk formats
/// (<c>docs/baseline/artifact-formats.md</c>). Read-only replay input: this slice adds no
/// generation behaviour, it projects pipeline output that already exists.
///
/// <paramref name="TerrainClassByTile"/> is row-major over the tile grid and holds the
/// Tiler's own terrain class (the <c>.maptiles</c> tile-id high byte:
/// 0=Water, 1=Land, 2=PineMountain, 3=RockMountain), not a palette index — mapping to the
/// preview palette is the projection's job, not the reader's.
///
/// <paramref name="Trees"/> is TreePlanter's canopy, read from the job's
/// <c>.worldpayload</c>. It is possibly empty — a Golden Job is discovered by its
/// <c>.maptiles</c>, which TreePlanter runs downstream of — but it is never null.
/// </summary>
public sealed record GoldenJobArtifacts(
    string JobId,
    int MapWidthInCells,
    int MapHeightInCells,
    int TileWidth,
    int TileHeight,
    IReadOnlyList<int> TerrainClassByTile,
    IReadOnlyList<GoldenStartZone> StartZones,
    IReadOnlyList<GoldenResourceCluster> ResourceClusters,
    IReadOnlyList<GoldenTree> Trees);

/// <summary>A <c>.playable.json</c> start zone. Coordinates are tile x/y.</summary>
public sealed record GoldenStartZone(string Id, int X, int Y);

/// <summary>
/// One tile TreePlanter planted (<c>.worldpayload</c> entry with a <c>tree</c> decoration).
/// Tile x/y. Variety is dropped: the prototype paints one canopy colour.
/// </summary>
public sealed record GoldenTree(int X, int Y);

/// <summary>A <c>.playable.json</c> resource cluster. Coordinates are tile x/y.</summary>
public sealed record GoldenResourceCluster(string Id, string Type, int X, int Y, string StartId);

/// <summary>
/// Port onto the golden-job fixtures. The application layer orchestrates and projects; the
/// filesystem adapter that actually reads the fixture bytes lives in the host, so no clock,
/// path, or file handle leaks into orchestration.
/// </summary>
public interface IGoldenJobSource
{
    /// <summary>The available job ids, in a stable order (replay selection is seed-driven).</summary>
    IReadOnlyList<string> JobIds { get; }

    /// <summary>Reads one job's artifacts. Throws if the fixture is missing or malformed.</summary>
    GoldenJobArtifacts Read(string jobId);
}
