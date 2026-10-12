using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>Collects the AMPB payload of a succeeded job.</summary>
public sealed class GetMapDocumentHandler
    : IRequestHandler<GetMapDocumentQuery, JobQueryResult<MapDocument>>
{
    private readonly WorldJobRegistry _registry;
    private readonly IGoldenJobSource _goldenJobs;

    public GetMapDocumentHandler(WorldJobRegistry registry, IGoldenJobSource goldenJobs)
    {
        _registry = registry;
        _goldenJobs = goldenJobs;
    }

    public ValueTask<JobQueryResult<MapDocument>> Handle(GetMapDocumentQuery query, CancellationToken cancellationToken)
        => ValueTask.FromResult(GoldenJobReplay.Collect(
            _registry,
            _goldenJobs,
            query.JobId,
            (job, artifacts) => WorldProjection.ToMapDocument(job, artifacts, _registry.Options.GeneratorVersion)));
}
