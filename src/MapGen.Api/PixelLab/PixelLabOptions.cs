namespace MapGen.Api.PixelLab;

public sealed class PixelLabOptions
{
    public required string RepositoryRoot { get; init; }
    public required string RunsRoot { get; init; }
    public required string GoldenFixturesRoot { get; init; }
    public string PythonExecutable { get; init; } = "python3";
    public string OrchestratorPath { get; init; } =
        "MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py";
    public string ClientPath { get; init; } =
        "MapGenerator/PixelLabPresentation/bin/pixellab_client.py";
    public string TokenEnvironmentVariable { get; init; } = "PIXELLAB_API_TOKEN";
}
