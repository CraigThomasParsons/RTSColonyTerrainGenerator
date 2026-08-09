using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>Lists recent jobs, newest first. A dev convenience, not part of ADR 0004.</summary>
public sealed class ListWorldJobsHandler
    : IRequestHandler<ListWorldJobsQuery, IReadOnlyList<JobStatus>>
{
    private readonly WorldJobRegistry _registry;

    public ListWorldJobsHandler(WorldJobRegistry registry) => _registry = registry;

    public ValueTask<IReadOnlyList<JobStatus>> Handle(ListWorldJobsQuery query, CancellationToken cancellationToken)
    {
        IReadOnlyList<JobStatus> statuses = _registry.All().Select(_registry.Describe).ToArray();
        return ValueTask.FromResult(statuses);
    }
}
