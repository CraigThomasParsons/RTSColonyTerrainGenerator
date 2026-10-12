using MapGen.Application.Common;
using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>
/// Validates a submission and records the job. Thin orchestration: no generation happens
/// here (or anywhere in this slice — the world endpoints replay golden jobs), and the reply
/// is the accepted job with the seed it was given, or the one the server picked.
/// </summary>
public sealed class SubmitWorldGenerationHandler
    : IRequestHandler<SubmitWorldGenerationCommand, Result<JobAccepted>>
{
    /// <summary>Generous, but bounded: a request is a map size, not a denial-of-service knob.</summary>
    private const int MaxCellsPerAxis = 1024;

    private readonly WorldJobRegistry _registry;

    public SubmitWorldGenerationHandler(WorldJobRegistry registry) => _registry = registry;

    public ValueTask<Result<JobAccepted>> Handle(SubmitWorldGenerationCommand command, CancellationToken cancellationToken)
        => ValueTask.FromResult(Submit(command));

    private Result<JobAccepted> Submit(SubmitWorldGenerationCommand command)
    {
        if (!IsValidAxis(command.MapWidthInCells, out string? widthError))
        {
            return Result<JobAccepted>.Fail($"map_width_in_cells {command.MapWidthInCells} is invalid: {widthError}");
        }

        if (!IsValidAxis(command.MapHeightInCells, out string? heightError))
        {
            return Result<JobAccepted>.Fail($"map_height_in_cells {command.MapHeightInCells} is invalid: {heightError}");
        }

        // Omitting the seed means the server picks one; the client always learns it back,
        // because determinism is only useful if the seed is knowable (ADR 0004 §4).
        long seed = command.Seed ?? Random.Shared.NextInt64(0, long.MaxValue);

        var job = _registry.Submit(seed, command.Name, command.MapWidthInCells, command.MapHeightInCells);
        var status = _registry.Describe(job);

        return Result<JobAccepted>.Ok(new JobAccepted(
            JobId: job.JobId,
            Status: status.Status,
            Seed: job.Seed,
            SubmittedAtUtc: job.SubmittedAtUtc));
    }

    private static bool IsValidAxis(int cells, out string? error)
    {
        if (cells <= 0)
        {
            error = "it must be greater than zero.";
            return false;
        }

        if (cells > MaxCellsPerAxis)
        {
            error = $"it must be at most {MaxCellsPerAxis}.";
            return false;
        }

        error = null;
        return true;
    }
}
