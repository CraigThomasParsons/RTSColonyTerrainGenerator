namespace MapGen.Application.WorldGeneration;

/// <summary>
/// The shared collect path: find the job, refuse to serve it before it has succeeded, read
/// the golden artifacts it replays, and project them. Both collect handlers differ only in
/// their projection, and the 404-vs-409 distinction is a contract detail worth stating once.
/// </summary>
internal static class GoldenJobReplay
{
    public static JobQueryResult<T> Collect<T>(
        WorldJobRegistry registry,
        IGoldenJobSource goldenJobs,
        string jobId,
        Func<WorldJob, GoldenJobArtifacts, T> project)
    {
        var job = registry.Find(jobId);
        if (job is null)
        {
            return JobQueryResult<T>.NotFound($"No job with id '{jobId}'.");
        }

        var status = registry.Describe(job);
        if (status.Status != Contracts.Worlds.WorldJobStatuses.Succeeded)
        {
            return JobQueryResult<T>.NotReady(
                $"Job '{jobId}' is '{status.Status}', not 'succeeded'; there is nothing to collect yet.");
        }

        GoldenJobArtifacts artifacts;
        try
        {
            artifacts = goldenJobs.Read(job.GoldenJobId);
        }
        catch (Exception e) when (e is IOException or InvalidDataException or UnauthorizedAccessException)
        {
            // Replay is the only thing that can fail in this slice, so it is the only route
            // to a 'failed' job. Record it so polling reports the same story as collecting.
            registry.MarkFailed(job, $"Could not replay golden job '{job.GoldenJobId}': {e.Message}");
            return JobQueryResult<T>.NotReady(job.Error!);
        }

        return JobQueryResult<T>.Ok(project(job, artifacts));
    }
}
