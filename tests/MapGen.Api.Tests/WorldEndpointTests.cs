using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using MapGen.Api.Tests.Support;
using MapGen.Application.WorldGeneration;

namespace MapGen.Api.Tests;

/// <summary>
/// The asynchronous world surface as the Wire Contract fixes it: submit → poll → collect.
/// These tests exist to make the shape non-negotiable — a submit that returned the map, or
/// a premature collect that 404'd or hung, would pass a laxer suite and break the client.
/// </summary>
public class WorldEndpointTests
{
    /// <summary>A factory whose jobs take real (simulated) time, for progression tests.</summary>
    private static MapGenApiFactory ProgressingFactory()
        => new() { Options = new WorldGenerationOptions { StageDuration = TimeSpan.FromSeconds(1) } };

    [Fact]
    public async Task Submit_returns_202_with_the_accepted_job_and_a_location_header()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/v1/worlds", new Dictionary<string, object?>
        {
            ["seed"] = 1234567890L,
            ["map_width_in_cells"] = 64,
            ["map_height_in_cells"] = 64,
            ["name"] = "Default Forest",
        });

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);

        var body = await response.ReadJson();
        Assert.Equal("queued", body.GetProperty("status").GetString());
        Assert.Equal(1234567890L, body.GetProperty("seed").GetInt64());
        Assert.Equal(MapGenApiFactory.Start, body.GetProperty("submitted_at_utc").GetDateTimeOffset());
        Assert.Equal($"/api/v1/worlds/{body.JobId()}", response.Headers.Location!.ToString());

        // The 202 body is the accepted job, never the map.
        Assert.DoesNotContain("terrain", body.PropertyNames());
        Assert.DoesNotContain("human_town_hall", body.PropertyNames());
    }

    [Fact]
    public async Task Submit_without_a_seed_picks_one_and_echoes_it_back()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/v1/worlds", new Dictionary<string, object?>
        {
            ["map_width_in_cells"] = 64,
            ["map_height_in_cells"] = 64,
        });

        var body = await response.ReadJson();
        Assert.True(body.GetProperty("seed").GetInt64() >= 0);
    }

    [Theory]
    [InlineData(0, 64)]
    [InlineData(64, -1)]
    [InlineData(4096, 64)]
    public async Task Submit_with_invalid_dimensions_is_a_400_problem(int width, int height)
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/v1/worlds", new Dictionary<string, object?>
        {
            ["map_width_in_cells"] = width,
            ["map_height_in_cells"] = height,
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType!.MediaType);

        var problem = await response.ReadJson();
        Assert.Equal("https://mapgen.local/problems/invalid-request", problem.GetProperty("type").GetString());
        Assert.Equal(400, problem.GetProperty("status").GetInt32());
        Assert.Contains("is invalid", problem.GetProperty("detail").GetString());
        Assert.Equal("/api/v1/worlds", problem.GetProperty("instance").GetString());
    }

    [Fact]
    public async Task A_job_walks_queued_then_running_with_a_stage_then_succeeded()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();
        string jobId = (await client.SubmitWorld()).JobId();

        var queued = await Poll(client, jobId);
        Assert.Equal("queued", queued.GetProperty("status").GetString());
        Assert.Equal(JsonValueKind.Null, queued.GetProperty("stage").ValueKind);
        Assert.Equal(0, queued.GetProperty("pct").GetInt32());
        Assert.Equal(JsonValueKind.Null, queued.GetProperty("completed_at_utc").ValueKind);

        factory.Clock.Advance(TimeSpan.FromSeconds(1));
        var running = await Poll(client, jobId);
        Assert.Equal("running", running.GetProperty("status").GetString());
        Assert.Equal("Heightmap", running.GetProperty("stage").GetString());

        factory.Clock.Advance(TimeSpan.FromSeconds(3));
        var laterRunning = await Poll(client, jobId);
        Assert.Equal("running", laterRunning.GetProperty("status").GetString());
        Assert.True(laterRunning.GetProperty("pct").GetInt32() >= running.GetProperty("pct").GetInt32(),
            "pct must be monotonically non-decreasing within a job.");

        factory.Clock.Advance(TimeSpan.FromSeconds(30));
        var succeeded = await Poll(client, jobId);
        Assert.Equal("succeeded", succeeded.GetProperty("status").GetString());
        Assert.Equal(100, succeeded.GetProperty("pct").GetInt32());
        Assert.NotEqual(JsonValueKind.Null, succeeded.GetProperty("completed_at_utc").ValueKind);
        Assert.Equal(JsonValueKind.Null, succeeded.GetProperty("error").ValueKind);
    }

    [Fact]
    public async Task Polling_an_unknown_job_is_a_404_problem()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        var response = await client.GetAsync("/api/v1/worlds/not-a-job");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType!.MediaType);
        Assert.Contains("not-a-job", (await response.ReadJson()).GetProperty("detail").GetString());
    }

    [Theory]
    [InlineData("map-document")]
    [InlineData("preview")]
    public async Task Collecting_before_the_job_succeeded_is_a_409_not_a_404_and_not_a_hang(string resource)
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();
        string jobId = (await client.SubmitWorld()).JobId();

        var response = await client.GetAsync($"/api/v1/worlds/{jobId}/{resource}");

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType!.MediaType);

        var problem = await response.ReadJson();
        Assert.Equal("https://mapgen.local/problems/job-not-ready", problem.GetProperty("type").GetString());
        Assert.Contains("not 'succeeded'", problem.GetProperty("detail").GetString());
    }

    [Theory]
    [InlineData("map-document")]
    [InlineData("preview")]
    public async Task Collecting_an_unknown_job_is_a_404(string resource)
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        var response = await client.GetAsync($"/api/v1/worlds/not-a-job/{resource}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Cancelling_stops_the_job_and_collection_stays_refused()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();
        string jobId = (await client.SubmitWorld()).JobId();
        factory.Clock.Advance(TimeSpan.FromSeconds(2));

        var cancelResponse = await client.DeleteAsync($"/api/v1/worlds/{jobId}");
        Assert.Equal(HttpStatusCode.Accepted, cancelResponse.StatusCode);
        Assert.Equal("cancelled", (await cancelResponse.ReadJson()).GetProperty("status").GetString());

        // A cancelled job stays cancelled however far the clock runs — it does not quietly
        // finish behind the client's back.
        factory.Clock.Advance(TimeSpan.FromMinutes(5));
        Assert.Equal("cancelled", (await Poll(client, jobId)).GetProperty("status").GetString());

        var collect = await client.GetAsync($"/api/v1/worlds/{jobId}/map-document");
        Assert.Equal(HttpStatusCode.Conflict, collect.StatusCode);
    }

    [Fact]
    public async Task Cancelling_an_unknown_job_is_a_404()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        Assert.Equal(HttpStatusCode.NotFound, (await client.DeleteAsync("/api/v1/worlds/not-a-job")).StatusCode);
    }

    [Fact]
    public async Task Listing_returns_submitted_jobs_newest_first()
    {
        using var factory = ProgressingFactory();
        using var client = factory.CreateClient();

        string first = (await client.SubmitWorld(seed: 1)).JobId();
        factory.Clock.Advance(TimeSpan.FromSeconds(1));
        string second = (await client.SubmitWorld(seed: 2)).JobId();

        var body = await (await client.GetAsync("/api/v1/worlds")).ReadJson();
        var ids = body.EnumerateArray().Select(job => job.GetProperty("job_id").GetString()).ToArray();

        Assert.Equal(new[] { second, first }, ids);
    }

    [Fact]
    public async Task A_job_whose_replay_fails_is_reported_as_failed_with_the_reason()
    {
        using var factory = new MapGenApiFactory { GoldenJobs = new UnreadableGoldenJobSource() };
        using var client = factory.CreateClient();
        string jobId = (await client.SubmitWorld()).JobId();

        var collect = await client.GetAsync($"/api/v1/worlds/{jobId}/map-document");
        Assert.Equal(HttpStatusCode.Conflict, collect.StatusCode);
        Assert.Contains("Could not replay golden job", (await collect.ReadJson()).GetProperty("detail").GetString());

        var status = await Poll(client, jobId);
        Assert.Equal("failed", status.GetProperty("status").GetString());
        Assert.Contains("Could not replay golden job", status.GetProperty("error").GetString());
    }

    private static async Task<JsonElement> Poll(HttpClient client, string jobId)
    {
        var response = await client.GetAsync($"/api/v1/worlds/{jobId}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return await response.ReadJson();
    }

    /// <summary>A fixture source whose artifacts cannot be read — the one route to 'failed'.</summary>
    private sealed class UnreadableGoldenJobSource : IGoldenJobSource
    {
        public IReadOnlyList<string> JobIds { get; } = new[] { "43860dcf-6469-42a7-9843-4e33abeacfac" };

        public GoldenJobArtifacts Read(string jobId)
            => throw new FileNotFoundException($"Golden-job artifact for '{jobId}' is missing.");
    }
}
