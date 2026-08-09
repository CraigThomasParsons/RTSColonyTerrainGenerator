namespace MapGen.Application.WorldGeneration;

/// <summary>How a lookup against the job table turned out.</summary>
public enum JobQueryOutcome
{
    /// <summary>The job exists and the requested payload is available.</summary>
    Found,

    /// <summary>No such job id.</summary>
    NotFound,

    /// <summary>The job exists but has not succeeded, so there is nothing to collect yet.</summary>
    NotReady,
}

/// <summary>
/// Three-way lookup outcome. <c>Result&lt;T&gt;</c> deliberately models only success and
/// failure, and the Wire Contract needs a premature collect (409) to be distinguishable
/// from an unknown job (404) — one is a timing mistake, the other a wrong id. Squeezing
/// both into a failure string would push that decision into string matching at the
/// transport, which is exactly the kind of thing that rots.
/// </summary>
public sealed record JobQueryResult<T>(JobQueryOutcome Outcome, T? Value, string? Error)
{
    public static JobQueryResult<T> Ok(T value) => new(JobQueryOutcome.Found, value, null);

    public static JobQueryResult<T> NotFound(string error) => new(JobQueryOutcome.NotFound, default, error);

    public static JobQueryResult<T> NotReady(string error) => new(JobQueryOutcome.NotReady, default, error);
}
