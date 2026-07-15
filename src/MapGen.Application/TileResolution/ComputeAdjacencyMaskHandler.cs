using MapGen.Application.Common;
using MapGen.Domain.TileResolution;
using Mediator;

namespace MapGen.Application.TileResolution;

/// <summary>
/// Thin orchestration: parse boundary input into a <see cref="TerrainGrid"/>, call the
/// domain, return an explicit result. The mask arithmetic lives solely in
/// <see cref="AdjacencyMaskCalculator"/> — reproducing it here is forbidden (AGENTS.md).
/// </summary>
public sealed class ComputeAdjacencyMaskHandler
    : IRequestHandler<ComputeAdjacencyMaskCommand, Result<AdjacencyMask>>
{
    public ValueTask<Result<AdjacencyMask>> Handle(ComputeAdjacencyMaskCommand command, CancellationToken cancellationToken)
        => ValueTask.FromResult(Compute(command));

    private static Result<AdjacencyMask> Compute(ComputeAdjacencyMaskCommand command)
    {
        TerrainGrid grid;
        try
        {
            grid = new TerrainGrid(command.GridWidth, command.GridHeight, command.Terrain);
        }
        catch (Exception e) when (e is ArgumentException or ArgumentOutOfRangeException)
        {
            return Result<AdjacencyMask>.Fail(e.Message);
        }

        if (!grid.Contains(command.CellX, command.CellY))
        {
            return Result<AdjacencyMask>.Fail(
                $"Cell ({command.CellX},{command.CellY}) is outside the cell map: " +
                $"the cell coordinate is outside the grid dimensions {grid.Width}×{grid.Height}.");
        }

        return Result<AdjacencyMask>.Ok(AdjacencyMaskCalculator.ComputeMask(grid, command.CellX, command.CellY));
    }
}
