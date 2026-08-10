using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>Reads one job's derived state. The poll the prototype client repeats.</summary>
public sealed class GetJobStatusHandler
    : IRequestHandler<GetJobStatusQuery, JobQueryResult<JobStatus>>
{
    private readonly WorldJobRegistry _registry;

    public GetJobStatusHandler(WorldJobRegistry registry) => _registry = registry;

    public ValueTask<JobQueryResult<JobStatus>> Handle(GetJobStatusQuery query, CancellationToken cancellationToken)
    {
        var job = _registry.Find(query.JobId);
        var result = job is null
            ? JobQueryResult<JobStatus>.NotFound($"No job with id '{query.JobId}'.")
            : JobQueryResult<JobStatus>.Ok(_registry.Describe(job));
        return ValueTask.FromResult(result);
    }
}
