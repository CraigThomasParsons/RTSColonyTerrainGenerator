using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>Collects the renderable preview of a succeeded job.</summary>
public sealed class GetMapPreviewHandler
    : IRequestHandler<GetMapPreviewQuery, JobQueryResult<MapPreview>>
{
    private readonly WorldJobRegistry _registry;
    private readonly IGoldenJobSource _goldenJobs;

    public GetMapPreviewHandler(WorldJobRegistry registry, IGoldenJobSource goldenJobs)
    {
        _registry = registry;
        _goldenJobs = goldenJobs;
    }

    public ValueTask<JobQueryResult<MapPreview>> Handle(GetMapPreviewQuery query, CancellationToken cancellationToken)
        => ValueTask.FromResult(GoldenJobReplay.Collect(
            _registry,
            _goldenJobs,
            query.JobId,
            WorldProjection.ToMapPreview));
}
