using MapGen.Application;
using MapGen.Application.Common;
using MapGen.Application.TileResolution;
using MapGen.Domain.TileResolution;
using Mediator;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace MapGen.Application.Tests;

/// <summary>
/// The composition root (ADR 0005) registers Mediator and this assembly's handlers, and
/// a command sent through <c>ISender</c> reaches its handler — the decoupling the CLI and
/// the future worker host rely on.
/// </summary>
public class MediatorWiringTests
{
    private static ISender BuildSender()
        => new ServiceCollection().AddMapGenApplication().BuildServiceProvider().GetRequiredService<ISender>();

    [Fact]
    public async Task Command_sent_through_ISender_is_handled()
    {
        var result = await BuildSender().Send(new ResolveTileRegionCommand(3, 4, 10, 10));

        Assert.True(result.IsSuccess);
        Assert.Equal(new TileCoordinate(6, 8), result.Value!.TopLeft);
    }

    [Fact]
    public async Task Invalid_command_dispatched_via_mediator_fails_without_throwing()
    {
        Result<TileRegion> result = await BuildSender().Send(new ResolveTileRegionCommand(10, 9, 10, 10));

        Assert.False(result.IsSuccess);
        Assert.Contains("outside the cell map", result.Error);
    }
}
