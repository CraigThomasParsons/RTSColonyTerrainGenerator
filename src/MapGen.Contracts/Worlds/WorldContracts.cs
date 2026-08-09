namespace MapGen.Contracts.Worlds;

/// <summary>
/// Submit a generation job. Field names are the golden job spec's
/// (<c>tests/fixtures/golden/*/input.job.json</c>), not ADR 0004's abbreviated sketch:
/// cells-vs-tiles ambiguity is exactly what the abbreviation loses.
///
/// <paramref name="Seed"/> is optional — omitted means the server picks one and echoes it
/// back, because determinism (ADR 0004 §4) requires the client always learn its seed.
/// </summary>
public sealed record GenerateWorldRequest(
    long? Seed,
    int MapWidthInCells,
    int MapHeightInCells,
    string? Name);

/// <summary>
/// The 202 body of <c>POST /worlds</c>. Generation is asynchronous: this is never the map.
/// </summary>
public sealed record JobAccepted(
    string JobId,
    string Status,
    long Seed,
    DateTimeOffset SubmittedAtUtc);

/// <summary>
/// The polled job state. <see cref="Status"/> is one of the lowercase strings in
/// <see cref="WorldJobStatuses"/> — never an enum ordinal, which is not a contract.
/// <see cref="Stage"/> is an opaque display string from <c>MapGenerator/stages.md</c>;
/// clients must not branch on it. <see cref="Error"/> is non-null iff the status is
/// <c>failed</c>.
/// </summary>
public sealed record JobStatus(
    string JobId,
    string Status,
    string? Stage,
    int Pct,
    long Seed,
    int MapWidthInCells,
    int MapHeightInCells,
    DateTimeOffset SubmittedAtUtc,
    DateTimeOffset? CompletedAtUtc,
    string? Error);

/// <summary>The wire vocabulary for <see cref="JobStatus.Status"/>.</summary>
public static class WorldJobStatuses
{
    public const string Queued = "queued";
    public const string Running = "running";
    public const string Succeeded = "succeeded";
    public const string Failed = "failed";
    public const string Cancelled = "cancelled";

    /// <summary>States after which a client stops polling.</summary>
    public static bool IsTerminal(string status)
        => status is Succeeded or Failed or Cancelled;
}

/// <summary>A position on the AMPB 64×64 tile grid. Row/col, never x/y (ADR 0004 §2).</summary>
public sealed record GridPosition(int Row, int Col);

/// <summary>An orc structure placement, as AMPB's map documents spell it.</summary>
public sealed record OrcBuilding(string Type, int Row, int Col, int TileSize);

/// <summary>A named, sized structure (mines) as AMPB's map documents spell it.</summary>
public sealed record NamedStructure(string Name, int Row, int Col, int TileSize);

/// <summary>
/// The AMPB map payload — the contract of ADR 0004 §2. Its body is the vocabulary observed
/// in AMPB <c>storage/app/maps/*.json</c> verbatim, plus the provenance block ADR 0004 §4
/// requires (<see cref="Seed"/>, <see cref="GeneratorVersion"/>, <see cref="JobId"/>).
///
/// The collections are always present and possibly empty — never omitted, never null — so
/// the client needs no null-coalescing. <see cref="Version"/> increments on any shape
/// change; clients assert it rather than parsing leniently.
/// </summary>
public sealed record MapDocument(
    int Version,
    string JobId,
    long Seed,
    string GeneratorVersion,
    string Slug,
    string Name,
    string Description,
    string ThumbnailColor,
    GridPosition HumanTownHall,
    IReadOnlyList<GridPosition> HumanWorkers,
    IReadOnlyList<OrcBuilding> OrcBuildings,
    IReadOnlyList<NamedStructure> Mines,
    IReadOnlyList<GridPosition> Trees,
    IReadOnlyList<GridPosition> Stones,
    IReadOnlyList<GridPosition> Roads);

/// <summary>A playable start zone, mirroring <c>.playable.json</c> minus the fields the
/// renderer has no use for. Coordinates are tile x/y.</summary>
public sealed record PreviewStartZone(string Id, int X, int Y);

/// <summary>A resource cluster, mirroring <c>.playable.json</c>. Coordinates are tile x/y.</summary>
public sealed record PreviewResourceCluster(string Id, string Type, int X, int Y, string StartId);

/// <summary>
/// One tile of TreePlanter's canopy from <c>.worldpayload</c>. Tile x/y on the same grid as
/// <see cref="MapPreview.Terrain"/>. Position list rather than a row-major mask: the
/// replayed jobs plant ~1k of 16 384 tiles (~45 KB preview). A mask pays around one-third
/// canopy coverage; a test guards that boundary.
/// </summary>
public sealed record PreviewTree(int X, int Y);

/// <summary>
/// The renderable preview. A <see cref="MapDocument"/> is entity placements and carries no
/// terrain grid at all, so the renderer cannot draw a map from one; extending it would
/// break ADR 0004's "v1 requires zero AMPB changes" rule. Hence a separate,
/// prototype-scoped resource.
///
/// <see cref="Terrain"/> is row-major (<c>index = y*width + x</c>, the convention
/// <c>TerrainGrid</c> already uses), of length <c>Width * Height</c>, holding indices into
/// <see cref="TerrainPalette"/>. Indices rather than strings keep a 128×128 preview at
/// ~16 KB of JSON instead of ~100 KB.
///
/// <see cref="Trees"/> follows the terrain because it is the other grid-scale layer and is
/// painted directly on top of it, beneath the zone and cluster markers.
/// </summary>
public sealed record MapPreview(
    int Version,
    string JobId,
    int Width,
    int Height,
    IReadOnlyList<string> TerrainPalette,
    IReadOnlyList<int> Terrain,
    IReadOnlyList<PreviewTree> Trees,
    IReadOnlyList<PreviewStartZone> StartZones,
    IReadOnlyList<PreviewResourceCluster> ResourceClusters);
