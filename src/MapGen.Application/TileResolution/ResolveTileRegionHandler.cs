using MapGen.Application.Common;
using MapGen.Domain.TileResolution;
using Mediator;

namespace MapGen.Application.TileResolution;

/// <summary>
/// Thin orchestration only: parse boundary input into value objects, call the domain,
/// return an explicit result. The expansion arithmetic lives solely in
/// <see cref="CellExpander"/> — reproducing it here is forbidden (AGENTS.md).
/// No persistence in this slice.
/// </summary>
public sealed class ResolveTileRegionHandler
    : IRequestHandler<ResolveTileRegionCommand, Result<TileRegion>>
{
    public ValueTask<Result<TileRegion>> Handle(ResolveTileRegionCommand command, CancellationToken cancellationToken)
        => ValueTask.FromResult(Resolve(command));

    private static Result<TileRegion> Resolve(ResolveTileRegionCommand command)
    {
        CellMapDimensions dimensions;
        CellCoordinate cell;

        try
        {
            dimensions = new CellMapDimensions(command.MapWidthInCells, command.MapHeightInCells);
            cell = new CellCoordinate(command.CellX, command.CellY);
        }
        catch (ArgumentOutOfRangeException e)
        {
            return Result<TileRegion>.Fail(e.Message);
        }

        if (!dimensions.Contains(cell))
        {
            return Result<TileRegion>.Fail(
                $"Cell ({cell.X},{cell.Y}) is outside the cell map: " +
                $"the cell coordinate is outside the cell map dimensions {dimensions.Width}×{dimensions.Height}.");
        }

        return Result<TileRegion>.Ok(CellExpander.Expand(cell, dimensions));
    }
}
