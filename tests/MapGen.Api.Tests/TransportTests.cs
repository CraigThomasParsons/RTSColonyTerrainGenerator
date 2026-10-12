using System.Net;
using MapGen.Api.Tests.Support;

namespace MapGen.Api.Tests;

/// <summary>
/// Transport-level obligations of the Wire Contract: the path version, the CORS allowance
/// for the Vite dev origin, and the OpenAPI document being a Development-only convenience.
/// </summary>
public class TransportTests
{
    [Fact]
    public async Task Every_endpoint_lives_under_the_versioned_base_path()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync("/worlds")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/v1/worlds")).StatusCode);
    }

    [Fact]
    public async Task The_vite_dev_origin_is_allowed_and_others_are_not()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var allowed = new HttpRequestMessage(HttpMethod.Get, "/api/v1/worlds");
        allowed.Headers.Add("Origin", "http://localhost:5190");
        var allowedResponse = await client.SendAsync(allowed);
        Assert.Equal("http://localhost:5190", allowedResponse.Headers.GetValues("Access-Control-Allow-Origin").Single());

        // The loopback literal is a distinct origin from localhost, and it is the one the
        // browser actually sends when the client is opened at http://127.0.0.1. Allowing
        // only the hostname form is indistinguishable from working until a browser tries.
        var loopback = new HttpRequestMessage(HttpMethod.Get, "/api/v1/worlds");
        loopback.Headers.Add("Origin", "http://127.0.0.1:5190");
        var loopbackResponse = await client.SendAsync(loopback);
        Assert.Equal("http://127.0.0.1:5190", loopbackResponse.Headers.GetValues("Access-Control-Allow-Origin").Single());

        var rejected = new HttpRequestMessage(HttpMethod.Get, "/api/v1/worlds");
        rejected.Headers.Add("Origin", "https://example.com");
        var rejectedResponse = await client.SendAsync(rejected);
        Assert.False(rejectedResponse.Headers.Contains("Access-Control-Allow-Origin"));
    }

    [Fact]
    public async Task The_openapi_document_is_served_in_development_only()
    {
        using var development = new MapGenApiFactory { Environment = "Development" };
        using var developmentClient = development.CreateClient();
        Assert.Equal(HttpStatusCode.OK, (await developmentClient.GetAsync("/openapi/v1.json")).StatusCode);

        using var testing = new MapGenApiFactory();
        using var testingClient = testing.CreateClient();
        Assert.Equal(HttpStatusCode.NotFound, (await testingClient.GetAsync("/openapi/v1.json")).StatusCode);
    }

    [Fact]
    public async Task An_adjacency_mask_request_without_terrain_is_a_400_not_a_500()
    {
        using var factory = new MapGenApiFactory();
        using var client = factory.CreateClient();

        var response = await client.PostJson("/api/v1/tiles/adjacency-mask",
            """{"cell_x":1,"cell_y":1,"grid_width":3,"grid_height":3}""");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Contains("terrain is required", (await response.ReadJson()).GetProperty("detail").GetString());
    }
}
