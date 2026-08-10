using MapGen.Api.Http;
using MapGen.Api.PixelLab;

namespace MapGen.Api.Endpoints;

public static class PixelLabEndpoints
{
    public static RouteGroupBuilder MapPixelLabEndpoints(this RouteGroupBuilder group)
    {
        group.MapGet("/pixellab/readiness", (IPixelLabJobService service) => Results.Ok(service.Readiness()));
        group.MapPost("/pixellab/readiness/balance", RefreshBalance);
        group.MapPost("/pixellab/jobs", Submit);
        group.MapGet("/pixellab/jobs/{jobId}", Get);
        group.MapPost("/pixellab/jobs/{jobId}/retry", Retry);
        group.MapPost("/pixellab/jobs/{jobId}/candidates/{candidateIndex:int}/approve",
            (string jobId, int candidateIndex, PixelLabDecisionRequest request, IPixelLabJobService service,
                HttpContext context, CancellationToken token) => Decide(jobId, candidateIndex, "approve", request, service, context, token));
        group.MapPost("/pixellab/jobs/{jobId}/candidates/{candidateIndex:int}/reject",
            (string jobId, int candidateIndex, PixelLabDecisionRequest request, IPixelLabJobService service,
                HttpContext context, CancellationToken token) => Decide(jobId, candidateIndex, "reject", request, service, context, token));
        group.MapGet("/pixellab/jobs/{jobId}/candidates/{candidateIndex:int}/image", Image);
        return group;
    }

    private static async Task<IResult> RefreshBalance(IPixelLabJobService service, HttpContext context,
        CancellationToken token)
    {
        try { return Results.Ok(await service.RefreshBalanceAsync(token)); }
        catch (InvalidOperationException error) { return ApiProblems.InvalidRequest(error.Message, context); }
    }

    private static async Task<IResult> Submit(CreatePixelLabJobRequest request, IPixelLabJobService service,
        HttpContext context, CancellationToken token)
    {
        try
        {
            PixelLabJobSnapshot snapshot = await service.SubmitAsync(request, token);
            return Results.Accepted($"/api/v1/pixellab/jobs/{snapshot.JobId}", snapshot);
        }
        catch (KeyNotFoundException error) { return ApiProblems.NotFound(error.Message, context); }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException)
        { return ApiProblems.InvalidRequest(error.Message, context); }
    }

    private static IResult Get(string jobId, IPixelLabJobService service, HttpContext context)
        => service.Find(jobId) is { } job ? Results.Ok(job) : ApiProblems.NotFound($"PixelLab job '{jobId}' was not found.", context);

    private static async Task<IResult> Retry(string jobId, IPixelLabJobService service, HttpContext context,
        CancellationToken token)
        => await service.RetryAsync(jobId, token) is { } job ? Results.Accepted($"/api/v1/pixellab/jobs/{jobId}", job)
            : ApiProblems.NotFound($"PixelLab job '{jobId}' was not found.", context);

    private static async Task<IResult> Decide(string jobId, int candidateIndex, string decision,
        PixelLabDecisionRequest request, IPixelLabJobService service, HttpContext context, CancellationToken token)
    {
        try
        {
            return await service.DecideAsync(jobId, candidateIndex, decision, request, token) is { } job
                ? Results.Ok(job) : ApiProblems.NotFound($"PixelLab job '{jobId}' was not found.", context);
        }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException)
        { return ApiProblems.InvalidRequest(error.Message, context); }
    }

    private static IResult Image(string jobId, int candidateIndex, IPixelLabJobService service,
        HttpContext context)
        => service.ResolveCandidateImage(jobId, candidateIndex) is { } path
            ? Results.File(path, "image/png", enableRangeProcessing: true)
            : ApiProblems.NotFound("The candidate image does not exist or is not eligible for review.", context);
}
