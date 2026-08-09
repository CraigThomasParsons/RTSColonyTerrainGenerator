using MapGen.Application.WorldGeneration;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace MapGen.Api.Tests.Support;

/// <summary>
/// Hosts the real MapGen.Api application in-process — the real routing, JSON options,
/// problem details, Mediator wiring, and the real golden-job fixtures on disk. Only the
/// clock (and, where a test needs a failure, the fixture source) is substituted.
/// </summary>
public sealed class MapGenApiFactory : WebApplicationFactory<Program>
{
    /// <summary>A fixed instant so submitted_at_utc is assertable.</summary>
    public static readonly DateTimeOffset Start = new(2026, 1, 28, 0, 42, 24, TimeSpan.Zero);

    public TestTimeProvider Clock { get; } = new(Start);

    /// <summary>Zero dwell means "already succeeded", which is what collect tests want.</summary>
    public WorldGenerationOptions Options { get; init; } = new() { StageDuration = TimeSpan.Zero };

    /// <summary>Set to substitute the fixture reader; null keeps the real one.</summary>
    public IGoldenJobSource? GoldenJobs { get; init; }

    /// <summary>Development turns on the OpenAPI document; everything else runs as Testing.</summary>
    public string Environment { get; init; } = "Testing";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment(Environment);
        // ConfigureTestServices runs after Program.cs has registered everything, so these
        // replacements win.
        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<TimeProvider>();
            services.AddSingleton<TimeProvider>(Clock);

            services.RemoveAll<WorldGenerationOptions>();
            services.AddSingleton(Options);

            if (GoldenJobs is not null)
            {
                services.RemoveAll<IGoldenJobSource>();
                services.AddSingleton(GoldenJobs);
            }
        });
    }
}
