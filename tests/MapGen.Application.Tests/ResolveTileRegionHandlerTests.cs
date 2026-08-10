using MapGen.Application.TileResolution;
using Xunit;

namespace MapGen.Application.Tests;

/// <summary>
/// The handler is orchestration only: valid input flows through to the domain; invalid
/// input becomes an explicit failure with a reason — never an escaping exception.
/// Exercised directly (the Mediator dispatch itself is covered by MediatorWiringTests).
/// </summary>
public class ResolveTileRegionHandlerTests
{
    private readonly ResolveTileRegionHandler _handler = new();

    [Fact]
    public async Task Valid_command_returns_the_domain_region()
    {
        var result = await _handler.Handle(new ResolveTileRegionCommand(3, 4, 10, 10), default);

        Assert.True(result.IsSuccess);
        Assert.Equal(6, result.Value!.TopLeft.X);
        Assert.Equal(8, result.Value!.TopLeft.Y);
        Assert.Equal(4, result.Value!.Coordinates.Count);
    }

    [Theory]
    [InlineData(10, 9, 10, 10)]   // x == width
    [InlineData(9, 10, 10, 10)]   // y == height
    [InlineData(-1, 0, 10, 10)]   // negative coordinate
    [InlineData(0, 0, 0, 10)]     // zero width
    [InlineData(0, 0, 10, -1)]    // negative height
    public async Task Invalid_command_fails_with_a_reason_not_an_exception(int x, int y, int width, int height)
    {
        var result = await _handler.Handle(new ResolveTileRegionCommand(x, y, width, height), default);

        Assert.False(result.IsSuccess);
        Assert.False(string.IsNullOrWhiteSpace(result.Error));
    }

    [Fact]
    public async Task Out_of_bounds_failure_names_the_reason_the_contract_requires()
    {
        var result = await _handler.Handle(new ResolveTileRegionCommand(10, 9, 10, 10), default);

        Assert.False(result.IsSuccess);
        Assert.Contains("outside the cell map", result.Error);
    }
}
