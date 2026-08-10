using System.Net;
using System.Text.Json;
using MapGen.Api.Tests.Support;

namespace MapGen.Api.Tests;

public class PixelLabEndpointTests
{
    [Fact]
    public async Task Development_host_announces_the_credit_free_interactive_transport()
    {
        using var factory = new MapGenApiFactory { Environment = "Development" };
        using var client = factory.CreateClient();
        JsonElement readiness = await (await client.GetAsync("/api/v1/pixellab/readiness")).ReadJson();
        Assert.Equal("development-fake", readiness.GetProperty("mode").GetString());
        Assert.Equal("fake credits", readiness.GetProperty("balance_currency").GetString());
        Assert.Contains("no PixelLab request", readiness.GetProperty("message").GetString());
    }

    [Fact]
    public async Task Fake_transport_runs_submit_review_approve_without_leaking_a_secret()
    {
        var fake = new FakePixelLabProcessExecutor();
        using var factory = new MapGenApiFactory { PixelLabExecutor = fake };
        using var client = factory.CreateClient();
        string worldJobId = await SubmitWorld(client);
        var submit = await client.PostJson("/api/v1/pixellab/jobs",
            $$"""{"world_job_id":"{{worldJobId}}","candidate_count":2,"candidate_budget":0,"mode":"offline","enable_live_calls":false,"confirm_credit_spend":false}""");
        Assert.Equal(HttpStatusCode.Accepted, submit.StatusCode);
        string jobId = (await submit.ReadJson()).GetProperty("job_id").GetString()!;
        JsonElement job = await PollTerminal(client, jobId);
        Assert.Equal("succeeded", job.GetProperty("status").GetString());
        Assert.Equal(1, job.GetProperty("cache_hits").GetInt32());
        Assert.Equal(1, job.GetProperty("submissions").GetInt32());
        Assert.StartsWith("/pixellab/jobs/",
            job.GetProperty("candidates")[0].GetProperty("image_url").GetString());

        await client.PostJson($"/api/v1/pixellab/jobs/{jobId}/candidates/1/approve",
            """{"actor":"Craig","reason":"First comparison choice."}""");
        var approvedResponse = await client.PostJson($"/api/v1/pixellab/jobs/{jobId}/candidates/0/approve",
            """{"actor":"Craig","reason":"Compared in Map Studio."}""");
        JsonElement approved = await approvedResponse.ReadJson();
        Assert.Equal("human-approved", approved.GetProperty("candidates")[0].GetProperty("state").GetString());
        Assert.Equal("rejected", approved.GetProperty("candidates")[1].GetProperty("state").GetString());
        Assert.Single(approved.GetProperty("candidates").EnumerateArray(), candidate =>
            candidate.GetProperty("state").GetString() == "human-approved");
        Assert.DoesNotContain(FakePixelLabProcessExecutor.FakeSecret, approved.GetRawText());
        var image = await client.GetAsync($"/api/v1/pixellab/jobs/{jobId}/candidates/0/image");
        Assert.Equal("image/png", image.Content.Headers.ContentType?.MediaType);
        Assert.NotEmpty(await image.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task Failed_fake_job_exposes_failure_and_retry_completes()
    {
        var fake = new FakePixelLabProcessExecutor { FailNextRun = true };
        using var factory = new MapGenApiFactory { PixelLabExecutor = fake };
        using var client = factory.CreateClient();
        string worldJobId = await SubmitWorld(client);
        string jobId = (await (await client.PostJson("/api/v1/pixellab/jobs",
            $$"""{"world_job_id":"{{worldJobId}}","candidate_count":1,"candidate_budget":0,"mode":"offline","enable_live_calls":false,"confirm_credit_spend":false}""")).ReadJson()).GetProperty("job_id").GetString()!;
        JsonElement failed = await PollTerminal(client, jobId);
        Assert.Equal("failed", failed.GetProperty("status").GetString());
        Assert.Contains("retry is safe", failed.GetProperty("error").GetString());
        var retry = await client.PostAsync($"/api/v1/pixellab/jobs/{jobId}/retry", null);
        Assert.Equal(HttpStatusCode.Accepted, retry.StatusCode);
        Assert.Equal("succeeded", (await retry.ReadJson()).GetProperty("status").GetString());
        Assert.Equal(2, fake.RunCount);
    }

    private static async Task<string> SubmitWorld(HttpClient client) =>
        (await (await client.PostJson("/api/v1/worlds",
            """{"seed":1,"map_width_in_cells":64,"map_height_in_cells":64}""")).ReadJson()).GetProperty("job_id").GetString()!;

    private static async Task<JsonElement> PollTerminal(HttpClient client, string jobId)
    {
        JsonElement job = default;
        for (int attempt = 0; attempt < 50; attempt++)
        {
            job = await (await client.GetAsync($"/api/v1/pixellab/jobs/{jobId}")).ReadJson();
            if (job.GetProperty("status").GetString() is "succeeded" or "failed") return job;
            await Task.Delay(10);
        }
        return job;
    }
}
