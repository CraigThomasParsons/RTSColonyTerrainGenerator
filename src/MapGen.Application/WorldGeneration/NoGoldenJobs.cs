namespace MapGen.Application.WorldGeneration;

/// <summary>
/// The default fixture source for hosts that do not serve the world endpoints — the CLI,
/// and any test that only exercises tile resolution. It reports no jobs, so a submission
/// fails loudly instead of a host silently appearing to generate worlds it cannot.
/// </summary>
internal sealed class NoGoldenJobs : IGoldenJobSource
{
    public IReadOnlyList<string> JobIds { get; } = Array.Empty<string>();

    public GoldenJobArtifacts Read(string jobId)
        => throw new InvalidOperationException(
            $"No golden-job source is configured, so job '{jobId}' cannot be replayed.");
}
