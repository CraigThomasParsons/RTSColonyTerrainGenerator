using System.Collections.Concurrent;
using MapGen.Contracts.Worlds;

namespace MapGen.Application.WorldGeneration;

/// <summary>
/// How the prototype narrates a replayed job. <see cref="StageDuration"/> is the dwell time
/// per stage: a job spends one such slot queued, then one per pipeline stage, then it has
/// succeeded. Zero means "succeeded the instant it was submitted", which is what endpoint
/// tests use when they care about collection rather than progression.
/// </summary>
public sealed class WorldGenerationOptions
{
    public TimeSpan StageDuration { get; init; } = TimeSpan.FromMilliseconds(300);

    /// <summary>Stamped into every <c>MapDocument</c> as provenance (ADR 0004 §4).</summary>
    public string GeneratorVersion { get; init; } = "0.1.0-prototype";
}

/// <summary>
/// One submitted job. Immutable except for cancellation, which is the only state a client
/// can push; everything else is derived from the clock by <see cref="WorldJobRegistry"/>.
/// </summary>
public sealed class WorldJob
{
    public required string JobId { get; init; }
    public required long Seed { get; init; }
    public required string? Name { get; init; }
    public required int MapWidthInCells { get; init; }
    public required int MapHeightInCells { get; init; }

    /// <summary>The golden job this run replays. Chosen from the seed, so it is deterministic.</summary>
    public required string GoldenJobId { get; init; }

    public required DateTimeOffset SubmittedAtUtc { get; init; }

    public DateTimeOffset? CancelledAtUtc { get; internal set; }

    /// <summary>Set only when replay itself failed — a missing or malformed fixture.</summary>
    public string? Error { get; internal set; }

    public DateTimeOffset? FailedAtUtc { get; internal set; }
}

/// <summary>
/// The in-memory job table for the prototype. Progress is a pure function of the injected
/// clock, so there are no timers, no background threads, and a test can step a job through
/// queued → running → succeeded deterministically.
///
/// Nothing here is domain behaviour: it tracks HTTP-visible job state and picks which
/// already-generated golden job a submission replays.
/// </summary>
public sealed class WorldJobRegistry
{
    /// <summary>
    /// The legacy stage names (<c>MapGenerator/stages.md</c>), reported only as opaque
    /// display strings — clients must not branch on them.
    /// </summary>
    public static readonly IReadOnlyList<string> Stages = new[]
    {
        "Heightmap",
        "WeatherAnalyses",
        "Tiler",
        "TreePlanter",
        "WorldFeatures",
        "PathFinder",
        "AncientCivilization",
        "Playable",
        "AgileMedievalExport",
    };

    private readonly ConcurrentDictionary<string, WorldJob> _jobs = new(StringComparer.Ordinal);
    private readonly TimeProvider _clock;
    private readonly WorldGenerationOptions _options;
    private readonly IGoldenJobSource _goldenJobs;

    public WorldJobRegistry(TimeProvider clock, WorldGenerationOptions options, IGoldenJobSource goldenJobs)
    {
        _clock = clock;
        _options = options;
        _goldenJobs = goldenJobs;
    }

    public WorldGenerationOptions Options => _options;

    public WorldJob Submit(long seed, string? name, int mapWidthInCells, int mapHeightInCells)
    {
        var job = new WorldJob
        {
            JobId = Guid.NewGuid().ToString(),
            Seed = seed,
            Name = name,
            MapWidthInCells = mapWidthInCells,
            MapHeightInCells = mapHeightInCells,
            GoldenJobId = SelectGoldenJob(seed),
            SubmittedAtUtc = _clock.GetUtcNow(),
        };

        _jobs[job.JobId] = job;
        return job;
    }

    public WorldJob? Find(string jobId)
        => _jobs.TryGetValue(jobId, out var job) ? job : null;

    /// <summary>Most recently submitted first — a dev convenience listing, not a contract.</summary>
    public IReadOnlyList<WorldJob> All()
        => _jobs.Values.OrderByDescending(job => job.SubmittedAtUtc).ToArray();

    /// <summary>Cancels a job. Already-terminal jobs are left alone; their state stands.</summary>
    public WorldJob Cancel(WorldJob job)
    {
        if (!WorldJobStatuses.IsTerminal(Describe(job).Status))
        {
            job.CancelledAtUtc = _clock.GetUtcNow();
        }
        return job;
    }

    /// <summary>Records that replay failed — the one way a prototype job reaches <c>failed</c>.</summary>
    public WorldJob MarkFailed(WorldJob job, string error)
    {
        job.Error = error;
        job.FailedAtUtc = _clock.GetUtcNow();
        return job;
    }

    /// <summary>The job's current wire status. Derived, so repeated calls stay consistent.</summary>
    public JobStatus Describe(WorldJob job)
    {
        var (status, stage, pct, completedAtUtc) = Progress(job);
        return new JobStatus(
            JobId: job.JobId,
            Status: status,
            Stage: stage,
            Pct: pct,
            Seed: job.Seed,
            MapWidthInCells: job.MapWidthInCells,
            MapHeightInCells: job.MapHeightInCells,
            SubmittedAtUtc: job.SubmittedAtUtc,
            CompletedAtUtc: completedAtUtc,
            Error: status == WorldJobStatuses.Failed ? job.Error : null);
    }

    public bool HasSucceeded(WorldJob job)
        => Describe(job).Status == WorldJobStatuses.Succeeded;

    private (string Status, string? Stage, int Pct, DateTimeOffset? CompletedAtUtc) Progress(WorldJob job)
    {
        if (job.FailedAtUtc is not null)
        {
            return (WorldJobStatuses.Failed, null, 100, job.FailedAtUtc);
        }

        // A cancelled job freezes at the moment it was cancelled rather than continuing to
        // advance with the clock.
        DateTimeOffset observedAt = job.CancelledAtUtc ?? _clock.GetUtcNow();
        string terminalStatus = job.CancelledAtUtc is null
            ? WorldJobStatuses.Succeeded
            : WorldJobStatuses.Cancelled;

        TimeSpan slot = _options.StageDuration;
        if (slot <= TimeSpan.Zero)
        {
            return (terminalStatus, Stages[^1], 100, observedAt);
        }

        // One slot queued, then one slot per stage.
        int totalSlots = Stages.Count + 1;
        TimeSpan elapsed = observedAt - job.SubmittedAtUtc;
        long slotIndex = elapsed.Ticks / slot.Ticks;

        if (slotIndex >= totalSlots)
        {
            var completedAtUtc = job.SubmittedAtUtc + (slot * totalSlots);
            return (terminalStatus, Stages[^1], 100, job.CancelledAtUtc ?? completedAtUtc);
        }

        int pct = (int)Math.Clamp(100L * elapsed.Ticks / (slot.Ticks * totalSlots), 0, 99);

        if (job.CancelledAtUtc is not null)
        {
            string? cancelledStage = slotIndex <= 0 ? null : Stages[(int)slotIndex - 1];
            return (WorldJobStatuses.Cancelled, cancelledStage, pct, job.CancelledAtUtc);
        }

        if (slotIndex <= 0)
        {
            return (WorldJobStatuses.Queued, null, 0, null);
        }

        return (WorldJobStatuses.Running, Stages[(int)slotIndex - 1], pct, null);
    }

    /// <summary>
    /// Which golden job a seed replays. Deterministic by construction: the same seed always
    /// yields the same map, which is the determinism ADR 0004 §4 asks of a real generator.
    /// </summary>
    private string SelectGoldenJob(long seed)
    {
        var ids = _goldenJobs.JobIds;
        if (ids.Count == 0)
        {
            throw new InvalidOperationException("No golden-job fixtures are available to replay.");
        }
        return ids[(int)((ulong)seed % (ulong)ids.Count)];
    }
}
