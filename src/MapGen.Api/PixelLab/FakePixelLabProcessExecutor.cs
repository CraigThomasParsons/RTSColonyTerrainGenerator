using System.Text.Json;

namespace MapGen.Api.PixelLab;

/// <summary>
/// Credit-free development transport for clicking through Map Studio. It is registered only
/// when Development configuration explicitly enables it; production never falls back to it.
/// </summary>
public sealed class FakePixelLabProcessExecutor : IPixelLabProcessExecutor
{
    public Task<PixelLabProcessResult> ExecuteAsync(PixelLabProcessRequest request,
        CancellationToken cancellationToken)
    {
        if (request.Command == "balance")
            return Task.FromResult(new PixelLabProcessResult(0,
                "{\"mode\":\"balance\",\"balance\":{\"amount\":999,\"currency\":\"fake credits\"}}", ""));

        string output = Value(request.Arguments, "--output");
        if (request.Command == "run")
        {
            int count = int.Parse(Value(request.Arguments, "--candidates"));
            Directory.CreateDirectory(output);
            File.WriteAllText(Path.Combine(output, "run-plan.json"), JsonSerializer.Serialize(new
            {
                candidates = Enumerable.Range(0, count).Select(index => new { candidateIndex = index, seed = index + 1 })
            }));
            for (int index = 0; index < count; index++) WriteCandidate(output, index);
            return Task.FromResult(new PixelLabProcessResult(0,
                $"{{\"submissions\":0,\"transport\":\"development-fake\",\"candidateCount\":{count}}}", ""));
        }

        int candidateIndex = int.Parse(Value(request.Arguments, "--candidate"));
        string directory = Path.Combine(output, "candidates", $"candidate-{candidateIndex:D3}");
        string state = request.Command == "approve" ? "human-approved" : "rejected";
        File.WriteAllText(Path.Combine(directory, "approval.json"), JsonSerializer.Serialize(new
        {
            currentState = state,
            decisions = new[] { new { actor = Value(request.Arguments, "--actor"), reason = Value(request.Arguments, "--reason") } }
        }));
        return Task.FromResult(new PixelLabProcessResult(0, $"{{\"currentState\":\"{state}\"}}", ""));
    }

    private static void WriteCandidate(string output, int index)
    {
        string directory = Path.Combine(output, "candidates", $"candidate-{index:D3}");
        Directory.CreateDirectory(directory);
        File.WriteAllBytes(Path.Combine(directory, "candidate.png"), PngFor(index));
        File.WriteAllText(Path.Combine(directory, "validation.json"),
            """{"structurallyValid":true,"eligibleForApproval":true,"resultingState":"generated","failures":[]}""");
        File.WriteAllText(Path.Combine(directory, "generation-manifest.json"),
            JsonSerializer.Serialize(new { remote = new { cacheHit = index > 0 } }));
    }

    private static byte[] PngFor(int index)
    {
        // Three small valid PNGs with distinct flat colours keep the GUI demo obvious.
        string[] images =
        [
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8zwAAAgEBAScY42YAAAAASUVORK5CYII=",
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z0rUAAAAASUVORK5CYII=",
        ];
        return Convert.FromBase64String(images[index % images.Length]);
    }

    private static string Value(IReadOnlyList<string> arguments, string name)
    {
        for (int index = 0; index < arguments.Count - 1; index++)
            if (arguments[index] == name) return arguments[index + 1];
        throw new InvalidOperationException($"Missing fake argument {name}.");
    }
}
