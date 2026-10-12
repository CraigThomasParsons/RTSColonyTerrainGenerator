using MapGen.Application.Common;
using MapGen.Contracts.Worlds;
using Mediator;

namespace MapGen.Application.WorldGeneration;

/// <summary>
/// Submit a generation job. Primitives at the boundary; the handler validates them and
/// returns an explicit result. A submission never blocks on generation — the reply is the
/// accepted job, never the map (ADR 0004).
/// </summary>
public sealed record SubmitWorldGenerationCommand(
    long? Seed,
    int MapWidthInCells,
    int MapHeightInCells,
    string? Name) : IRequest<Result<JobAccepted>>;

/// <summary>Poll one job's state.</summary>
public sealed record GetJobStatusQuery(string JobId) : IRequest<JobQueryResult<JobStatus>>;

/// <summary>Collect the AMPB payload. Available only once the job has succeeded.</summary>
public sealed record GetMapDocumentQuery(string JobId) : IRequest<JobQueryResult<MapDocument>>;

/// <summary>Collect the renderable preview. Available only once the job has succeeded.</summary>
public sealed record GetMapPreviewQuery(string JobId) : IRequest<JobQueryResult<MapPreview>>;

/// <summary>Cancel an in-flight job. A prototype affordance, not part of ADR 0004.</summary>
public sealed record CancelWorldGenerationCommand(string JobId) : IRequest<JobQueryResult<JobStatus>>;

/// <summary>List recent jobs. A prototype affordance, not part of ADR 0004.</summary>
public sealed record ListWorldJobsQuery : IRequest<IReadOnlyList<JobStatus>>;
