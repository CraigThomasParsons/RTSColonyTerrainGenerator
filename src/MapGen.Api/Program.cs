using System.Text.Json;
using System.Text.Json.Serialization;
using MapGen.Api.Endpoints;
using MapGen.Api.Replay;
using MapGen.Application;
using MapGen.Application.WorldGeneration;

// MapGen.Api is the transport shell over MapGen.Application (ADR 0004). It adds no domain
// behaviour: every endpoint dispatches an existing CQRS request through Mediator (ADR 0005)
// and maps the result onto a status code.
//
// It is internal by construction — Kestrel binds loopback only (appsettings.json) and CORS
// allows exactly the Vite dev origin. In Phase 2 the Laravel BFF (Backend For Frontend) becomes the only caller.
var builder = WebApplication.CreateBuilder(args);

// Registered before AddMapGenApplication so its TryAdd defaults defer to the host's real
// collaborators: the API serves the world endpoints, so it owns the clock, the replay
// options, and the fixture reader.
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(new WorldGenerationOptions
{
    StageDuration = builder.Configuration.GetValue("MapGen:WorldGeneration:StageDuration", TimeSpan.FromMilliseconds(300)),
    GeneratorVersion = builder.Configuration.GetValue("MapGen:WorldGeneration:GeneratorVersion", "0.1.0-prototype")!,
});
builder.Services.AddSingleton<IGoldenJobSource>(_ => new GoldenJobFileSource(
    GoldenFixtures.ResolveRoot(builder.Configuration["MapGen:GoldenFixturesRoot"], builder.Environment.ContentRootPath)));

builder.Services.AddMapGenApplication();

// snake_case across the whole surface: the map document must be snake_case because AMPB
// consumes it verbatim, and one convention beats a mixed one.
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.Never;
});

builder.Services.AddProblemDetails();
builder.Services.AddOpenApi();

const string DevClientCorsPolicy = "vite-dev-client";
string[] devClientOrigins = builder.Configuration.GetSection("MapGen:DevClientOrigins").Get<string[]>()
    ?? new[] { "http://localhost:5173", "http://127.0.0.1:5173" };

builder.Services.AddCors(options => options.AddPolicy(
    DevClientCorsPolicy,
    policy => policy.WithOrigins(devClientOrigins).AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseCors(DevClientCorsPolicy);

if (app.Environment.IsDevelopment())
{
    // Describes the Wire Contract; it does not define it. Development only.
    app.MapOpenApi();
}

var v1 = app.MapGroup("/api/v1");
v1.MapWorldEndpoints();
v1.MapTileEndpoints();

app.Run();

/// <summary>
/// Locates the read-only golden-job fixtures. Configuration wins; otherwise walk up from
/// the content root to the repository marker, so the API runs from any working directory.
/// </summary>
internal static class GoldenFixtures
{
    private const string RepositoryMarker = "MapGen.slnx";

    public static string ResolveRoot(string? configuredRoot, string contentRootPath)
    {
        if (!string.IsNullOrWhiteSpace(configuredRoot))
        {
            return configuredRoot;
        }

        var directory = new DirectoryInfo(contentRootPath);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, RepositoryMarker)))
        {
            directory = directory.Parent;
        }

        string repositoryRoot = directory?.FullName ?? contentRootPath;
        return Path.Combine(repositoryRoot, "tests", "fixtures", "golden");
    }
}

/// <summary>Exposed so endpoint tests can host this exact application (WebApplicationFactory).</summary>
public partial class Program;
