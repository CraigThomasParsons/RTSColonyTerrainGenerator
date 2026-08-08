using System.Text;
using MapGen.Contracts.Worlds;

namespace MapGen.Application.WorldGeneration;

/// <summary>
/// Projects a replayed golden job into the two collect payloads. Projection only — it
/// reproduces no domain arithmetic and touches no fixture; it renames, halves, and filters
/// what the legacy pipeline already produced.
/// </summary>
public static class WorldProjection
{
    /// <summary>
    /// The current shape version of both collect payloads. Version 2 adds the replayed
    /// canopy: <c>MapPreview</c> gains a <c>trees</c> layer, and <c>MapDocument.Trees</c>
    /// stops being the <c>wood</c> resource clusters and becomes TreePlanter's forest.
    /// </summary>
    public const int DocumentVersion = 2;

    /// <summary>
    /// The <c>.worldpayload</c> terrain vocabulary, in the order the preview indexes into.
    /// </summary>
    public static readonly IReadOnlyList<string> TerrainPalette = new[]
    {
        "deep_water", "water", "dirt", "grass", "rock", "mountain",
    };

    /// <summary>
    /// Tiler terrain class (<c>.maptiles</c> tile-id high byte) to palette index.
    /// The Tiler classifies four terrains; <c>deep_water</c> and <c>dirt</c> exist in the
    /// palette because <c>.worldpayload</c> emits them, and stay unused until a stage that
    /// produces them is replayed.
    /// </summary>
    private static readonly int[] PaletteIndexByTerrainClass =
    {
        1, // Water        -> water
        3, // Land         -> grass
        5, // PineMountain -> mountain
        4, // RockMountain -> rock
    };

    /// <summary>AMPB's default map thumbnail swatch; the prototype has no palette sampler.</summary>
    private const string ThumbnailColor = "#3a5a2a";

    /// <summary>Every structure AMPB sizes is 4 tiles across in its own documents.</summary>
    private const int StructureTileSize = 4;

    public static MapPreview ToMapPreview(WorldJob job, GoldenJobArtifacts artifacts)
    {
        var terrain = new int[artifacts.TerrainClassByTile.Count];
        for (int i = 0; i < terrain.Length; i++)
        {
            int terrainClass = artifacts.TerrainClassByTile[i];
            terrain[i] = terrainClass >= 0 && terrainClass < PaletteIndexByTerrainClass.Length
                ? PaletteIndexByTerrainClass[terrainClass]
                : PaletteIndexByTerrainClass[0];
        }

        return new MapPreview(
            Version: DocumentVersion,
            JobId: job.JobId,
            Width: artifacts.TileWidth,
            Height: artifacts.TileHeight,
            TerrainPalette: TerrainPalette,
            Terrain: terrain,
            Trees: artifacts.Trees
                .Select(tree => new PreviewTree(tree.X, tree.Y))
                .ToArray(),
            StartZones: artifacts.StartZones
                .Select(zone => new PreviewStartZone(zone.Id, zone.X, zone.Y))
                .ToArray(),
            ResourceClusters: artifacts.ResourceClusters
                .Select(cluster => new PreviewResourceCluster(cluster.Id, cluster.Type, cluster.X, cluster.Y, cluster.StartId))
                .ToArray());
    }

    /// <summary>
    /// The AMPB payload. Playable coordinates are tile x/y on the 128×128 tile grid; AMPB
    /// documents are row/col on the 64×64 grid, so the export halves and transposes here —
    /// server-side, exactly as the Wire Contract requires. The client never sees x/y in a
    /// map document.
    /// </summary>
    public static MapDocument ToMapDocument(WorldJob job, GoldenJobArtifacts artifacts, string generatorVersion)
    {
        int gridWidth = Math.Max(1, artifacts.TileWidth / 2);
        int gridHeight = Math.Max(1, artifacts.TileHeight / 2);

        // The first start zone is the human settlement; every other zone is an opponent.
        var startZones = artifacts.StartZones;
        GridPosition townHall = startZones.Count > 0
            ? ToGridPosition(startZones[0].X, startZones[0].Y, gridWidth, gridHeight)
            : new GridPosition(0, 0);

        var orcBuildings = startZones
            .Skip(1)
            .Select(zone => ToGridPosition(zone.X, zone.Y, gridWidth, gridHeight))
            .Select(position => new OrcBuilding("town_hall", position.Row, position.Col, StructureTileSize))
            .ToArray();

        var mines = artifacts.ResourceClusters
            .Where(cluster => cluster.Type == "ore")
            .Select((cluster, index) =>
            {
                var position = ToGridPosition(cluster.X, cluster.Y, gridWidth, gridHeight);
                return new NamedStructure($"Mine #{index + 1}", position.Row, position.Col, StructureTileSize);
            })
            .ToArray();

        // TreePlanter's canopy, not the `wood` resource clusters it used to be filtered out
        // of: those are the handful of harvest sites Playable marks near each start, so a
        // 128×128 map exported with as many trees as it had wood piles. Four tile positions
        // collapse onto one 64×64 grid cell, so the projection distinguishes them once.
        var trees = artifacts.Trees
            .Select(tree => ToGridPosition(tree.X, tree.Y, gridWidth, gridHeight))
            .Distinct()
            .ToArray();

        string name = string.IsNullOrWhiteSpace(job.Name) ? DefaultName(job.JobId) : job.Name!;

        return new MapDocument(
            Version: DocumentVersion,
            JobId: job.JobId,
            Seed: job.Seed,
            GeneratorVersion: generatorVersion,
            Slug: Slugify(name),
            Name: name,
            Description: $"Generated by MapGen job {ShortId(job.JobId)}.",
            ThumbnailColor: ThumbnailColor,
            HumanTownHall: townHall,
            // The replayed fixtures carry no workers, stone, or roads. The collections stay
            // present and empty rather than absent: the contract's strict reading.
            HumanWorkers: Array.Empty<GridPosition>(),
            OrcBuildings: orcBuildings,
            Mines: mines,
            Trees: trees,
            Stones: Array.Empty<GridPosition>(),
            Roads: Array.Empty<GridPosition>());
    }

    private static GridPosition ToGridPosition(int tileX, int tileY, int gridWidth, int gridHeight)
        => new(
            Row: Math.Clamp(tileY / 2, 0, gridHeight - 1),
            Col: Math.Clamp(tileX / 2, 0, gridWidth - 1));

    private static string DefaultName(string jobId) => $"Map {ShortId(jobId)}";

    private static string ShortId(string jobId) => jobId.Length <= 8 ? jobId : jobId[..8];

    private static string Slugify(string name)
    {
        var slug = new StringBuilder(name.Length);
        foreach (char c in name.ToLowerInvariant())
        {
            if (char.IsAsciiLetterOrDigit(c))
            {
                slug.Append(c);
            }
            else if (slug.Length > 0 && slug[^1] != '_')
            {
                slug.Append('_');
            }
        }
        return slug.ToString().Trim('_');
    }
}
