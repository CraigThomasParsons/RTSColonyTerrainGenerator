using MapGen.Api.Http;
using MapGen.Application.TileResolution;
using MapGen.Contracts.Tiles;
using Mediator;

namespace MapGen.Api.Endpoints;

/// <summary>
/// The synchronous tile surface. These are the only endpoints in this slice backed by real
/// verified domain code: they wrap the two existing CQRS commands unchanged, which are
/// already primitives-only records at the boundary and so model-bind directly — no request
/// DTO is invented for them.
///
/// POST rather than GET because <c>adjacency-mask</c> carries a row-major terrain array
/// that does not belong in a query string; <c>expand-cell</c> matches it for symmetry.
/// </summary>
public static class TileEndpoints
{
    public static RouteGroupBuilder MapTileEndpoints(this RouteGroupBuilder group)
    {
        group.MapPost("/tiles/expand-cell", ExpandCell)
            .WithName("ExpandCell")
            .WithSummary("Resolve the 2×2 tile region of one cell, ordered TL, TR, BL, BR.");

        group.MapPost("/tiles/adjacency-mask", AdjacencyMask)
            .WithName("AdjacencyMask")
            .WithSummary("Compute the 4-bit adjacency mask of one cell (N=1, E=2, S=4, W=8).");

        return group;
    }

    private static async Task<IResult> ExpandCell(ResolveTileRegionCommand command, ISender sender, HttpContext context)
    {
        var result = await sender.Send(command);
        if (!result.IsSuccess)
        {
            // Handler failures here are validation failures by construction: the handlers
            // catch ArgumentException and return Fail, so a failure is never a server fault.
            return ApiProblems.InvalidRequest(result.Error!, context);
        }

        var region = result.Value!;
        return Results.Ok(new TileRegionResponse(
            Cell: new TilePosition(command.CellX, command.CellY),
            Tiles: region.Coordinates.Select(tile => new TilePosition(tile.X, tile.Y)).ToArray()));
    }

    private static async Task<IResult> AdjacencyMask(ComputeAdjacencyMaskCommand command, ISender sender, HttpContext context)
    {
        if (command.Terrain is null)
        {
            // An absent array is a malformed request, not a domain question: the handler
            // parses terrain, it does not conjure it.
            return ApiProblems.InvalidRequest("terrain is required: a row-major array of grid_width × grid_height values.", context);
        }

        var result = await sender.Send(command);
        if (!result.IsSuccess)
        {
            return ApiProblems.InvalidRequest(result.Error!, context);
        }

        var mask = result.Value!;
        return Results.Ok(new AdjacencyMaskResponse(
            Cell: new TilePosition(command.CellX, command.CellY),
            Mask: mask.Value,
            North: mask.HasNorth,
            East: mask.HasEast,
            South: mask.HasSouth,
            West: mask.HasWest));
    }
}
