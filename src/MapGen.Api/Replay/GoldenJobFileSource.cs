using System.Text.Json;
using MapGen.Application.WorldGeneration;

namespace MapGen.Api.Replay;

/// <summary>
/// Reads the golden-job fixtures off disk, strictly read-only. This is the host's adapter,
/// not application logic: it parses the on-disk formats catalogued in
/// <c>docs/baseline/artifact-formats.md</c> and hands the application layer plain data.
///
/// Nothing here writes, moves, or rewrites a fixture — the fixtures are the migration
/// baseline and this slice only replays them.
/// </summary>
public sealed class GoldenJobFileSource : IGoldenJobSource
{
    private const uint MapTilesMagic = 0x4C49544D; // "MTIL" little-endian
    private const int MapTilesHeaderBytes = 32;

    private readonly string _fixturesRoot;
    private readonly Lazy<IReadOnlyList<string>> _jobIds;

    public GoldenJobFileSource(string fixturesRoot)
    {
        _fixturesRoot = fixturesRoot;
        _jobIds = new Lazy<IReadOnlyList<string>>(DiscoverJobIds);
    }

    /// <summary>The fixtures directory this source reads. Surfaced for diagnostics.</summary>
    public string FixturesRoot => _fixturesRoot;

    public IReadOnlyList<string> JobIds => _jobIds.Value;

    public GoldenJobArtifacts Read(string jobId)
    {
        string jobDirectory = Path.Combine(_fixturesRoot, jobId);
        var (tileWidth, tileHeight, terrainClassByTile) =
            ReadMapTiles(Path.Combine(jobDirectory, $"{jobId}.maptiles"));
        var (startZones, resourceClusters) =
            ReadPlayable(Path.Combine(jobDirectory, $"{jobId}.playable.json"));
        var (cellWidth, cellHeight) = ReadJobSpec(Path.Combine(jobDirectory, "input.job.json"));

        return new GoldenJobArtifacts(
            JobId: jobId,
            MapWidthInCells: cellWidth,
            MapHeightInCells: cellHeight,
            TileWidth: tileWidth,
            TileHeight: tileHeight,
            TerrainClassByTile: terrainClassByTile,
            StartZones: startZones,
            ResourceClusters: resourceClusters);
    }

    private IReadOnlyList<string> DiscoverJobIds()
    {
        if (!Directory.Exists(_fixturesRoot))
        {
            return Array.Empty<string>();
        }

        return Directory.EnumerateDirectories(_fixturesRoot)
            .Select(Path.GetFileName)
            .Where(name => name is not null && File.Exists(Path.Combine(_fixturesRoot, name, $"{name}.maptiles")))
            .Select(name => name!)
            .Order(StringComparer.Ordinal)
            .ToArray();
    }

    /// <summary>
    /// <c>.maptiles</c>: 32-byte header ("MTIL", version, tile_width, tile_height, seed,
    /// tile_count, reserved) then u16 tile ids, row-major. The tile id's high byte is the
    /// Tiler's terrain class and the low nibble is the adjacency mask.
    /// </summary>
    private static (int Width, int Height, int[] TerrainClassByTile) ReadMapTiles(string path)
    {
        byte[] bytes = ReadAllBytes(path);
        if (bytes.Length < MapTilesHeaderBytes)
        {
            throw new InvalidDataException($"'{path}' is shorter than a .maptiles header.");
        }

        uint magic = BitConverter.ToUInt32(bytes, 0);
        if (magic != MapTilesMagic)
        {
            throw new InvalidDataException($"'{path}' is not a .maptiles file (bad magic).");
        }

        int width = BitConverter.ToInt32(bytes, 8);
        int height = BitConverter.ToInt32(bytes, 12);
        int count = BitConverter.ToInt32(bytes, 24);

        if (width <= 0 || height <= 0 || count != width * height)
        {
            throw new InvalidDataException(
                $"'{path}' declares {width}×{height} tiles but a tile count of {count}.");
        }

        if (bytes.Length < MapTilesHeaderBytes + (2 * count))
        {
            throw new InvalidDataException($"'{path}' is truncated: {count} tile ids do not fit.");
        }

        var terrainClassByTile = new int[count];
        for (int i = 0; i < count; i++)
        {
            terrainClassByTile[i] = BitConverter.ToUInt16(bytes, MapTilesHeaderBytes + (2 * i)) >> 8;
        }

        return (width, height, terrainClassByTile);
    }

    private static (GoldenStartZone[] StartZones, GoldenResourceCluster[] ResourceClusters) ReadPlayable(string path)
    {
        using var document = ParseJson(path);
        var root = document.RootElement;

        var startZones = ReadArray(root, "start_zones", element => new GoldenStartZone(
            element.GetProperty("id").GetString()!,
            element.GetProperty("x").GetInt32(),
            element.GetProperty("y").GetInt32()));

        var resourceClusters = ReadArray(root, "resource_clusters", element => new GoldenResourceCluster(
            element.GetProperty("id").GetString()!,
            element.GetProperty("type").GetString()!,
            element.GetProperty("x").GetInt32(),
            element.GetProperty("y").GetInt32(),
            element.GetProperty("start_id").GetString()!));

        return (startZones, resourceClusters);
    }

    private static (int Width, int Height) ReadJobSpec(string path)
    {
        using var document = ParseJson(path);
        var root = document.RootElement;
        return (
            root.GetProperty("map_width_in_cells").GetInt32(),
            root.GetProperty("map_height_in_cells").GetInt32());
    }

    // A malformed fixture is bad data, not a programming error: report it as such so the
    // job is marked failed rather than crashing the request.
    private static JsonDocument ParseJson(string path)
    {
        try
        {
            return JsonDocument.Parse(ReadAllText(path));
        }
        catch (Exception e) when (e is JsonException or KeyNotFoundException)
        {
            throw new InvalidDataException($"'{path}' is not readable as JSON: {e.Message}", e);
        }
    }

    private static T[] ReadArray<T>(JsonElement root, string property, Func<JsonElement, T> read)
    {
        if (!root.TryGetProperty(property, out var array) || array.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<T>();
        }
        return array.EnumerateArray().Select(read).ToArray();
    }

    // Missing fixtures surface as IOException so the application layer can mark the job
    // failed rather than the host throwing a 500 at the client.
    private static byte[] ReadAllBytes(string path)
    {
        RequireFile(path);
        return File.ReadAllBytes(path);
    }

    private static string ReadAllText(string path)
    {
        RequireFile(path);
        return File.ReadAllText(path);
    }

    private static void RequireFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException($"Golden-job artifact '{path}' is missing.", path);
        }
    }
}
