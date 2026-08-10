using MapGen.Application.Common;
using MapGen.Domain.TileResolution;
using Mediator;

namespace MapGen.Application.TileResolution;

/// <summary>
/// Compute the 4-bit adjacency mask for one cell of a terrain grid. Primitives at the
/// boundary (terrain row-major); the handler parses them into a <see cref="TerrainGrid"/>
/// so malformed input becomes an explicit failure. Dispatched through Mediator (ADR 0005).
/// </summary>
public sealed record ComputeAdjacencyMaskCommand(
    int CellX,
    int CellY,
    int GridWidth,
    int GridHeight,
    IReadOnlyList<int> Terrain) : IRequest<Result<AdjacencyMask>>;
