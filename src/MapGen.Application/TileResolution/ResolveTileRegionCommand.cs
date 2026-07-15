using MapGen.Application.Common;
using MapGen.Domain.TileResolution;
using Mediator;

namespace MapGen.Application.TileResolution;

/// <summary>
/// Resolve the 2×2 tile region for one cell. Primitives at the boundary; the handler
/// parses them into domain value objects (parse-don't-validate) so invalid input
/// becomes an explicit failure, not an exception escaping the seam.
///
/// Dispatched through Mediator (ADR 0005): callers depend on <c>ISender</c>, never on
/// the concrete handler.
/// </summary>
public sealed record ResolveTileRegionCommand(
    int CellX,
    int CellY,
    int MapWidthInCells,
    int MapHeightInCells) : IRequest<Result<TileRegion>>;
