using System.Net;
using System.Text.Json;
using MapGen.Api.Tests.Support;

namespace MapGen.Api.Tests;

/// <summary>
/// What a succeeded job hands back. The client's TypeScript types are hand-written against
/// the Wire Contract, so these assertions are that mirror's server-side guard: exact key
/// sets, snake_case names, and the row/col-versus-x/y rule.
///
/// The payloads are projections of the golden-job fixtures — real pipeline output, read
/// only.
/// </summary>
public class CollectedPayloadTests
{
    // The default factory's StageDuration is zero, so a submitted job has already succeeded.
    private static async Task<JsonElement> Collect(HttpClient client, string resource, long seed = 1234567890)
    {
        string jobId = (await client.SubmitWorld(seed: seed)).JobId();
        Assert.Equal("succeeded", (await (await client.GetAsync($"/api/v1/worlds/{jobId}")).ReadJson())
            .GetProperty("status").GetString());

        var response = await client.GetAsync($"/api/v1/worlds/{jobId}/{resource}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("application/json", response.Content.Headers.ContentType!.MediaType);
        return await response.ReadJson();
    }

    [Fact]
    public async Task The_map_document_carries_exactly_the_contracted_keys()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var document = await Collect(client, "map-document");

        Assert.Equal(new[]
        {
            "version", "job_id", "seed", "generator_version",
            "slug", "name", "description", "thumbnail_color",
            "human_town_hall", "human_workers", "orc_buildings", "mines",
            "trees", "stones", "roads",
        }, document.PropertyNames());

        Assert.Equal(2, document.GetProperty("version").GetInt32());
        Assert.Equal(1234567890L, document.GetProperty("seed").GetInt64());
        Assert.Equal("0.1.0-prototype", document.GetProperty("generator_version").GetString());
        Assert.Equal("Default Forest", document.GetProperty("name").GetString());
        Assert.Equal("default_forest", document.GetProperty("slug").GetString());
    }

    [Fact]
    public async Task Map_document_positions_are_row_col_on_the_64_by_64_grid_never_x_y()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var document = await Collect(client, "map-document");

        var townHall = document.GetProperty("human_town_hall");
        Assert.Equal(new[] { "row", "col" }, townHall.PropertyNames());
        AssertOnGrid(townHall);

        foreach (var building in document.GetProperty("orc_buildings").EnumerateArray())
        {
            Assert.Equal(new[] { "type", "row", "col", "tile_size" }, building.PropertyNames());
            AssertOnGrid(building);
        }

        foreach (var mine in document.GetProperty("mines").EnumerateArray())
        {
            Assert.Equal(new[] { "name", "row", "col", "tile_size" }, mine.PropertyNames());
            AssertOnGrid(mine);
        }

        foreach (var tree in document.GetProperty("trees").EnumerateArray())
        {
            Assert.Equal(new[] { "row", "col" }, tree.PropertyNames());
            AssertOnGrid(tree);
        }
    }

    [Fact]
    public async Task Map_document_collections_are_present_and_never_null()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var document = await Collect(client, "map-document");

        foreach (string collection in new[] { "human_workers", "orc_buildings", "mines", "trees", "stones", "roads" })
        {
            Assert.Equal(JsonValueKind.Array, document.GetProperty(collection).ValueKind);
        }
    }

    [Fact]
    public async Task The_preview_carries_a_row_major_terrain_grid_indexed_into_the_palette()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var preview = await Collect(client, "preview");

        Assert.Equal(new[]
        {
            "version", "job_id", "width", "height",
            "terrain_palette", "terrain", "trees", "start_zones", "resource_clusters",
        }, preview.PropertyNames());

        Assert.Equal(2, preview.GetProperty("version").GetInt32());
        Assert.Equal(
            new[] { "deep_water", "water", "dirt", "grass", "rock", "mountain" },
            preview.GetProperty("terrain_palette").EnumerateArray().Select(entry => entry.GetString()).ToArray());

        int width = preview.GetProperty("width").GetInt32();
        int height = preview.GetProperty("height").GetInt32();

        // The golden jobs are 64×64 cells, and tile dimensions are twice the cell
        // dimensions per axis — the client must read the grid size from here, never infer
        // it from what it requested.
        Assert.Equal(128, width);
        Assert.Equal(128, height);

        var terrain = preview.GetProperty("terrain").EnumerateArray().Select(entry => entry.GetInt32()).ToArray();
        Assert.Equal(width * height, terrain.Length);
        Assert.All(terrain, index => Assert.InRange(index, 0, 5));

        // The fixtures are real terrain: a preview of one uniform value would mean the
        // maptiles reader silently produced nothing useful.
        Assert.True(terrain.Distinct().Count() > 1, "the replayed terrain should not be uniform.");
    }

    [Fact]
    public async Task Preview_zones_and_clusters_mirror_the_playable_fixture_in_tile_x_y()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var preview = await Collect(client, "preview");

        var zones = preview.GetProperty("start_zones").EnumerateArray().ToArray();
        Assert.NotEmpty(zones);
        foreach (var zone in zones)
        {
            // Minus the fields the renderer has no use for: no slope, no settlement labels.
            Assert.Equal(new[] { "id", "x", "y" }, zone.PropertyNames());
        }

        var clusters = preview.GetProperty("resource_clusters").EnumerateArray().ToArray();
        Assert.NotEmpty(clusters);
        foreach (var cluster in clusters)
        {
            Assert.Equal(new[] { "id", "type", "x", "y", "start_id" }, cluster.PropertyNames());
        }
    }

    [Fact]
    public async Task The_preview_carries_TreePlanters_canopy_in_tile_x_y()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var preview = await Collect(client, "preview");

        int width = preview.GetProperty("width").GetInt32();
        int height = preview.GetProperty("height").GetInt32();

        var trees = preview.GetProperty("trees").EnumerateArray().ToArray();

        // The canopy is a forest, not the two wood clusters the preview used to show. A
        // handful of trees here would mean the .worldpayload was not read.
        Assert.True(trees.Length > 100, $"the replayed canopy should be a forest, not {trees.Length} trees.");

        foreach (var tree in trees)
        {
            // The preview is the one document that speaks x/y, and these are tile
            // coordinates on the same grid the terrain array is indexed by.
            Assert.Equal(new[] { "x", "y" }, tree.PropertyNames());
            Assert.InRange(tree.GetProperty("x").GetInt32(), 0, width - 1);
            Assert.InRange(tree.GetProperty("y").GetInt32(), 0, height - 1);
        }
    }

    [Fact]
    public async Task The_preview_stays_small_enough_to_carry_the_canopy_as_positions()
    {
        // The canopy is a position list rather than a row-major mask alongside the terrain.
        // That holds while the forest is sparse; this is the tripwire for when it stops
        // holding, because at that point the mask is the cheaper shape.
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        string jobId = (await client.SubmitWorld()).JobId();
        var response = await client.GetAsync($"/api/v1/worlds/{jobId}/preview");
        long bytes = (await response.Content.ReadAsByteArrayAsync()).LongLength;

        Assert.True(bytes < 1024 * 1024, $"the preview is {bytes} bytes; a canopy bitmask would be cheaper.");
    }

    [Fact]
    public async Task The_map_document_carries_the_real_canopy_not_the_wood_clusters()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var document = await Collect(client, "map-document");
        var preview = await Collect(client, "preview");

        var trees = document.GetProperty("trees").EnumerateArray().ToArray();
        int woodClusters = preview.GetProperty("resource_clusters").EnumerateArray()
            .Count(cluster => cluster.GetProperty("type").GetString() == "wood");

        // The bug this replaces: trees were the resource clusters filtered by type, so a
        // 128x128 map exported with as many trees as it had wood piles.
        Assert.True(
            trees.Length > woodClusters * 10,
            $"the document canopy ({trees.Length}) should not be the {woodClusters} wood clusters.");

        // Four tile positions collapse onto one 64x64 grid cell, so a repeat would be a
        // position AMPB has no use for twice.
        var positions = trees
            .Select(tree => (tree.GetProperty("row").GetInt32(), tree.GetProperty("col").GetInt32()))
            .ToArray();
        Assert.Equal(positions.Length, positions.Distinct().Count());
    }

    [Fact]
    public async Task The_same_seed_replays_the_same_map()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var first = await Collect(client, "map-document", seed: 77);
        var second = await Collect(client, "map-document", seed: 77);

        Assert.Equal(
            first.GetProperty("human_town_hall").GetRawText(),
            second.GetProperty("human_town_hall").GetRawText());
        Assert.Equal(
            first.GetProperty("mines").GetRawText(),
            second.GetProperty("mines").GetRawText());

        // Same map, different runs: the job id is the one thing that must differ.
        Assert.NotEqual(first.JobId(), second.JobId());
    }

    [Fact]
    public async Task Different_seeds_can_replay_different_maps()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var documents = new List<string>();
        for (long seed = 0; seed < 3; seed++)
        {
            documents.Add((await Collect(client, "map-document", seed: seed))
                .GetProperty("human_town_hall").GetRawText());
        }

        Assert.True(documents.Distinct().Count() > 1,
            "seeds should select different golden jobs, so the maps should not all be identical.");
    }

    private static void AssertOnGrid(JsonElement position)
    {
        Assert.InRange(position.GetProperty("row").GetInt32(), 0, 63);
        Assert.InRange(position.GetProperty("col").GetInt32(), 0, 63);
    }
}
