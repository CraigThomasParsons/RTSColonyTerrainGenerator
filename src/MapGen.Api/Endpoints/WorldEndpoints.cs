using MapGen.Api.Http;
using MapGen.Application.WorldGeneration;
using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Api.Endpoints;

/// <summary>
/// The asynchronous world surface: submit → poll → collect. A submit never returns a map
/// (202), and a collect before the job succeeded is a 409, never a 404 and never a hang.
/// Transport only — every decision below is a mapping from an application result to a
/// status code.
/// </summary>
public static class WorldEndpoints
{
    public static RouteGroupBuilder MapWorldEndpoints(this RouteGroupBuilder group)
    {
        group.MapPost("/worlds", SubmitWorld)
            .WithName("SubmitWorld")
            .WithSummary("Submit a generation job. Returns 202 and the accepted job, never the map.");

        group.MapGet("/worlds/{jobId}", GetWorldStatus)
            .WithName("GetWorldStatus")
            .WithSummary("Poll a job's status. Terminal states are succeeded, failed, cancelled.");

        group.MapGet("/worlds/{jobId}/map-document", GetMapDocument)
            .WithName("GetMapDocument")
            .WithSummary("Collect the AMPB map payload. 409 until the job has succeeded.");

        group.MapGet("/worlds/{jobId}/preview", GetMapPreview)
            .WithName("GetMapPreview")
            .WithSummary("Collect the renderable preview. 409 until the job has succeeded.");

        group.MapDelete("/worlds/{jobId}", CancelWorld)
            .WithName("CancelWorld")
            .WithSummary("PROTOTYPE AFFORDANCE (not part of ADR 0004): cancel an in-flight job.");

        group.MapGet("/worlds", ListWorlds)
            .WithName("ListWorlds")
            .WithSummary("PROTOTYPE AFFORDANCE (not part of ADR 0004): list recent jobs, newest first.");

        return group;
    }

    private static async Task<IResult> SubmitWorld(GenerateWorldRequest request, ISender sender, HttpContext context)
    {
        var result = await sender.Send(new SubmitWorldGenerationCommand(
            Seed: request.Seed,
            MapWidthInCells: request.MapWidthInCells,
            MapHeightInCells: request.MapHeightInCells,
            Name: request.Name));

        if (!result.IsSuccess)
        {
            return ApiProblems.InvalidRequest(result.Error!, context);
        }

        var accepted = result.Value!;
        return Results.Accepted($"/api/v1/worlds/{accepted.JobId}", accepted);
    }

    private static async Task<IResult> GetWorldStatus(string jobId, ISender sender, HttpContext context)
        => Respond(await sender.Send(new GetJobStatusQuery(jobId)), context);

    private static async Task<IResult> GetMapDocument(string jobId, ISender sender, HttpContext context)
        => Respond(await sender.Send(new GetMapDocumentQuery(jobId)), context);

    private static async Task<IResult> GetMapPreview(string jobId, ISender sender, HttpContext context)
        => Respond(await sender.Send(new GetMapPreviewQuery(jobId)), context);

    private static async Task<IResult> CancelWorld(string jobId, ISender sender, HttpContext context)
    {
        var result = await sender.Send(new CancelWorldGenerationCommand(jobId));
        if (result.Outcome == JobQueryOutcome.NotFound)
        {
            return ApiProblems.NotFound(result.Error!, context);
        }
        return Results.Accepted($"/api/v1/worlds/{jobId}", result.Value);
    }

    private static async Task<IResult> ListWorlds(ISender sender)
        => Results.Ok(await sender.Send(new ListWorldJobsQuery()));

    private static IResult Respond<T>(JobQueryResult<T> result, HttpContext context)
        => result.Outcome switch
        {
            JobQueryOutcome.Found => Results.Ok(result.Value),
            JobQueryOutcome.NotFound => ApiProblems.NotFound(result.Error!, context),
            JobQueryOutcome.NotReady => ApiProblems.NotReady(result.Error!, context),
            _ => throw new InvalidOperationException($"Unhandled job query outcome '{result.Outcome}'."),
        };
}
