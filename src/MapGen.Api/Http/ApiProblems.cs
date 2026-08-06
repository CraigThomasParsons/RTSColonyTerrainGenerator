namespace MapGen.Api.Http;

/// <summary>
/// The one place non-2xx responses are shaped. Every failure is RFC 7807
/// <c>application/problem+json</c>, and the <c>detail</c> is the handler's own message —
/// those are human-readable by construction, so the transport invents no second vocabulary.
/// </summary>
public static class ApiProblems
{
    private const string TypeBase = "https://mapgen.local/problems/";

    public static IResult InvalidRequest(string detail, HttpContext context)
        => Problem("invalid-request", "Invalid request", StatusCodes.Status400BadRequest, detail, context);

    public static IResult NotFound(string detail, HttpContext context)
        => Problem("job-not-found", "Job not found", StatusCodes.Status404NotFound, detail, context);

    /// <summary>A collect before the job succeeded: a timing mistake, distinguishable from a bad id.</summary>
    public static IResult NotReady(string detail, HttpContext context)
        => Problem("job-not-ready", "Job is not ready", StatusCodes.Status409Conflict, detail, context);

    private static IResult Problem(string slug, string title, int status, string detail, HttpContext context)
        => Results.Problem(
            type: TypeBase + slug,
            title: title,
            statusCode: status,
            detail: detail,
            instance: context.Request.Path);
}
