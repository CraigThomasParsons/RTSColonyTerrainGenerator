using System.Net;
using MapGen.Api.Tests.Support;

namespace MapGen.Api.Tests;

/// <summary>
/// The two endpoints backed by real verified domain code, so these assert real behaviour —
/// the expansion order CellToTile.dfy proves, and the mask bits AdjacencyMask.dfy defines —
/// not just plumbing.
/// </summary>
public class TileEndpointTests
{
    [Fact]
    public async Task Expand_cell_returns_the_four_tiles_in_TL_TR_BL_BR_order()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var response = await client.PostJson("/api/v1/tiles/expand-cell",
            """{"cell_x":3,"cell_y":4,"map_width_in_cells":10,"map_height_in_cells":10}""");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = await response.ReadJson();
        Assert.Equal(new[] { "cell", "tiles" }, body.PropertyNames());
        Assert.Equal(3, body.GetProperty("cell").GetProperty("x").GetInt32());
        Assert.Equal(4, body.GetProperty("cell").GetProperty("y").GetInt32());

        var tiles = body.GetProperty("tiles").EnumerateArray()
            .Select(tile => (tile.GetProperty("x").GetInt32(), tile.GetProperty("y").GetInt32()))
            .ToArray();

        Assert.Equal(new[] { (6, 8), (7, 8), (6, 9), (7, 9) }, tiles);
    }

    [Fact]
    public async Task Expand_cell_outside_the_map_is_a_400_carrying_the_domain_message()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var response = await client.PostJson("/api/v1/tiles/expand-cell",
            """{"cell_x":12,"cell_y":3,"map_width_in_cells":10,"map_height_in_cells":10}""");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType!.MediaType);

        var problem = await response.ReadJson();
        Assert.Equal("/api/v1/tiles/expand-cell", problem.GetProperty("instance").GetString());
        // The client maps detail straight to the UI, so it must be the domain's own wording.
        Assert.Equal(
            "Cell (12,3) is outside the cell map: the cell coordinate is outside the cell map dimensions 10×10.",
            problem.GetProperty("detail").GetString());
    }

    [Fact]
    public async Task Adjacency_mask_of_a_uniform_interior_cell_is_fully_connected()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var response = await client.PostJson("/api/v1/tiles/adjacency-mask",
            """{"cell_x":1,"cell_y":1,"grid_width":3,"grid_height":3,"terrain":[1,1,1,1,1,1,1,1,1]}""");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = await response.ReadJson();
        Assert.Equal(new[] { "cell", "mask", "north", "east", "south", "west" }, body.PropertyNames());
        Assert.Equal(15, body.GetProperty("mask").GetInt32());
        Assert.True(body.GetProperty("north").GetBoolean());
        Assert.True(body.GetProperty("east").GetBoolean());
        Assert.True(body.GetProperty("south").GetBoolean());
        Assert.True(body.GetProperty("west").GetBoolean());
    }

    [Fact]
    public async Task Adjacency_mask_bits_follow_the_terrain_not_merely_the_grid_edges()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        // Centre cell is land; only its western neighbour matches.
        var response = await client.PostJson("/api/v1/tiles/adjacency-mask",
            """{"cell_x":1,"cell_y":1,"grid_width":3,"grid_height":3,"terrain":[0,0,0,1,1,0,0,0,0]}""");

        var body = await response.ReadJson();
        Assert.Equal(8, body.GetProperty("mask").GetInt32());
        Assert.True(body.GetProperty("west").GetBoolean());
        Assert.False(body.GetProperty("north").GetBoolean());
        Assert.False(body.GetProperty("east").GetBoolean());
        Assert.False(body.GetProperty("south").GetBoolean());
    }

    [Fact]
    public async Task Adjacency_mask_with_a_terrain_array_that_does_not_fit_the_grid_is_a_400()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var response = await client.PostJson("/api/v1/tiles/adjacency-mask",
            """{"cell_x":1,"cell_y":1,"grid_width":3,"grid_height":3,"terrain":[1,1,1]}""");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType!.MediaType);
        Assert.False(string.IsNullOrWhiteSpace((await response.ReadJson()).GetProperty("detail").GetString()));
    }
}
