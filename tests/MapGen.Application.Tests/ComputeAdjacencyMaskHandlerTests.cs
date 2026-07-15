using MapGen.Application.TileResolution;
using Xunit;

namespace MapGen.Application.Tests;

/// <summary>
/// Orchestration only: valid input flows through to the domain; malformed grids and
/// out-of-bounds cells become explicit failures with a reason, never exceptions.
/// </summary>
public class ComputeAdjacencyMaskHandlerTests
{
    private readonly ComputeAdjacencyMaskHandler _handler = new();

    private static int[] AllSame3x3 => new[] { 1, 1, 1, 1, 1, 1, 1, 1, 1 };

    [Fact]
    public async Task Interior_all_same_returns_mask_15()
    {
        var result = await _handler.Handle(new ComputeAdjacencyMaskCommand(1, 1, 3, 3, AllSame3x3), default);

        Assert.True(result.IsSuccess);
        Assert.Equal(15, result.Value!.Value);
    }

    [Fact]
    public async Task Terrain_length_mismatch_fails_with_a_reason()
    {
        var result = await _handler.Handle(new ComputeAdjacencyMaskCommand(0, 0, 3, 3, new[] { 1, 1, 1 }), default);

        Assert.False(result.IsSuccess);
        Assert.False(string.IsNullOrWhiteSpace(result.Error));
    }

    [Fact]
    public async Task Out_of_bounds_cell_fails_with_the_contract_reason()
    {
        var result = await _handler.Handle(new ComputeAdjacencyMaskCommand(3, 1, 3, 3, AllSame3x3), default);

        Assert.False(result.IsSuccess);
        Assert.Contains("outside the cell map", result.Error);
    }
}
