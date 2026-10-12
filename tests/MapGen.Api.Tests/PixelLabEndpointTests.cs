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

    [Fact]
    public async Task Evaluation_is_digest_bound_persistent_and_exposes_only_allowlisted_evidence()
    {
        var fake = new FakePixelLabProcessExecutor();
        using var factory = new MapGenApiFactory { PixelLabExecutor = fake };
        using var client = factory.CreateClient();
        string worldJobId = await SubmitWorld(client);
        string jobId = (await (await client.PostJson("/api/v1/pixellab/jobs",
            $$"""{"world_job_id":"{{worldJobId}}","candidate_count":1,"candidate_budget":0,"mode":"offline","enable_live_calls":false,"confirm_credit_spend":false}""")).ReadJson())
            .GetProperty("job_id").GetString()!;
        await PollTerminal(client, jobId);
        await ApproveCandidate(client, jobId);

        JsonElement bundle = await (await client.GetAsync($"/api/v1/pixellab/jobs/{jobId}/evaluation")).ReadJson();
        JsonElement candidate = bundle.GetProperty("candidates")[0];
        Assert.Equal(1, bundle.GetProperty("version").GetInt32());
        Assert.True(candidate.GetProperty("eligible_for_evaluation").GetBoolean());
        Assert.Equal("not-observed", candidate.GetProperty("cost").GetProperty("status").GetString());
        Assert.Equal("not-observed", candidate.GetProperty("latency").GetProperty("status").GetString());

        var response = await client.PostJson(
            $"/api/v1/pixellab/jobs/{jobId}/candidates/0/evaluation",
            """{"reviewer":"Craig","rationale":"Compared every authoritative overlay.","verdict":"accept","scores":{"shoreline_fidelity":5,"traversability_cues":4,"starts_and_resources":5,"visual_cohesion":4,"gameplay_readability":5}}""");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        JsonElement reviewed = await response.ReadJson();
        Assert.True(reviewed.GetProperty("reviews")[0].GetProperty("current").GetBoolean());
        JsonElement replacement = await (await client.PostJson(
            $"/api/v1/pixellab/jobs/{jobId}/candidates/0/evaluation",
            """{"reviewer":"Craig","rationale":"Replaced after a second careful comparison.","verdict":"reject","scores":{"shoreline_fidelity":3,"traversability_cues":3,"starts_and_resources":4,"visual_cohesion":3,"gameplay_readability":4}}""")).ReadJson();
        Assert.Single(replacement.GetProperty("reviews").EnumerateArray());
        Assert.Equal("reject", replacement.GetProperty("reviews")[0].GetProperty("verdict").GetString());
        Assert.Equal(0, fake.NetworkRequests);
        Assert.Equal(0, fake.PaidSubmissions);

        var semantic = await client.GetAsync(
            $"/api/v1/pixellab/jobs/{jobId}/candidates/0/evidence/semantic-control");
        Assert.Equal("image/png", semantic.Content.Headers.ContentType?.MediaType);
        var forbidden = await client.GetAsync(
            $"/api/v1/pixellab/jobs/{jobId}/candidates/0/evidence/evaluation.json");
        Assert.Equal(HttpStatusCode.NotFound, forbidden.StatusCode);
    }

    [Fact]
    public async Task Changed_candidate_invalidates_existing_evaluation_and_bad_scores_fail_closed()
    {
        var fake = new FakePixelLabProcessExecutor();
        using var factory = new MapGenApiFactory { PixelLabExecutor = fake };
        using var client = factory.CreateClient();
        string worldJobId = await SubmitWorld(client);
        string jobId = (await (await client.PostJson("/api/v1/pixellab/jobs",
            $$"""{"world_job_id":"{{worldJobId}}","candidate_count":1,"candidate_budget":0,"mode":"offline","enable_live_calls":false,"confirm_credit_spend":false}""")).ReadJson())
            .GetProperty("job_id").GetString()!;
        await PollTerminal(client, jobId);
        await ApproveCandidate(client, jobId);

        var bad = await client.PostJson($"/api/v1/pixellab/jobs/{jobId}/candidates/0/evaluation",
            """{"reviewer":"Craig","rationale":"Bad score must fail.","verdict":"accept","scores":{"shoreline_fidelity":6,"traversability_cues":4,"starts_and_resources":5,"visual_cohesion":4,"gameplay_readability":5}}""");
        Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);

        await client.PostJson($"/api/v1/pixellab/jobs/{jobId}/candidates/0/evaluation",
            """{"reviewer":"Craig","rationale":"Initial digest review.","verdict":"accept","scores":{"shoreline_fidelity":5,"traversability_cues":4,"starts_and_resources":5,"visual_cohesion":4,"gameplay_readability":5}}""");
        fake.ChangeCandidate(jobId);
        JsonElement refreshed = await (await client.GetAsync($"/api/v1/pixellab/jobs/{jobId}/evaluation")).ReadJson();
        Assert.False(refreshed.GetProperty("candidates")[0].GetProperty("reviews")[0]
            .GetProperty("current").GetBoolean());
    }

    [Fact]
    public async Task Generated_but_unapproved_candidate_cannot_be_evaluated()
    {
        using var factory = new MapGenApiFactory { PixelLabExecutor = new FakePixelLabProcessExecutor() };
        using var client = factory.CreateClient();
        string worldJobId = await SubmitWorld(client);
        string jobId = (await (await client.PostJson("/api/v1/pixellab/jobs",
            $$"""{"world_job_id":"{{worldJobId}}","candidate_count":1,"candidate_budget":0,"mode":"offline","enable_live_calls":false,"confirm_credit_spend":false}""")).ReadJson())
            .GetProperty("job_id").GetString()!;
        await PollTerminal(client, jobId);

        var response = await client.PostJson(
            $"/api/v1/pixellab/jobs/{jobId}/candidates/0/evaluation",
            """{"reviewer":"Craig","rationale":"Approval evidence is deliberately absent.","verdict":"reject","scores":{"shoreline_fidelity":3,"traversability_cues":3,"starts_and_resources":3,"visual_cohesion":3,"gameplay_readability":3}}""");
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Contains("complete evidence", (await response.ReadJson()).GetProperty("detail").GetString());
    }

    private static async Task<string> SubmitWorld(HttpClient client) =>
        (await (await client.PostJson("/api/v1/worlds",
            """{"seed":1,"map_width_in_cells":64,"map_height_in_cells":64}""")).ReadJson()).GetProperty("job_id").GetString()!;

    private static async Task ApproveCandidate(HttpClient client, string jobId) =>
        _ = await client.PostJson($"/api/v1/pixellab/jobs/{jobId}/candidates/0/approve",
            """{"actor":"Craig","reason":"Selected for experimental evaluation."}""");

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
