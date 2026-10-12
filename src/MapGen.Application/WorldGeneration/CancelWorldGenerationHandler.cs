using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>
/// Cancels an in-flight job. A prototype affordance: Phase 2 may drop it without a version
/// bump. Cancelling an already-terminal job is a no-op that reports the state it is in.
/// </summary>
public sealed class CancelWorldGenerationHandler
    : IRequestHandler<CancelWorldGenerationCommand, JobQueryResult<JobStatus>>
{
    private readonly WorldJobRegistry _registry;

    public CancelWorldGenerationHandler(WorldJobRegistry registry) => _registry = registry;

    public ValueTask<JobQueryResult<JobStatus>> Handle(CancelWorldGenerationCommand command, CancellationToken cancellationToken)
    {
        var job = _registry.Find(command.JobId);
        if (job is null)
        {
            return ValueTask.FromResult(JobQueryResult<JobStatus>.NotFound($"No job with id '{command.JobId}'."));
        }

        return ValueTask.FromResult(JobQueryResult<JobStatus>.Ok(_registry.Describe(_registry.Cancel(job))));
    }
}
