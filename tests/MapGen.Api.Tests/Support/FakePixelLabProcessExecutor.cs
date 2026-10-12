using System.Text.Json;
using MapGen.Api.PixelLab;

namespace MapGen.Api.Tests.Support;

public sealed class FakePixelLabProcessExecutor : IPixelLabProcessExecutor
{
    public const string FakeSecret = "FAKE-PIXELLAB-TOKEN-MUST-NOT-LEAK";
    public bool FailNextRun { get; set; }
    public int RunCount { get; private set; }
    public int NetworkRequests { get; private set; }
    public int PaidSubmissions { get; private set; }
    private string? _lastOutput;

    public Task<PixelLabProcessResult> ExecuteAsync(PixelLabProcessRequest request, CancellationToken cancellationToken)
    {
        if (request.Command == "balance")
            return Task.FromResult(new PixelLabProcessResult(0,
                "{\"mode\":\"balance\",\"balance\":{\"amount\":12.5,\"currency\":\"credits\"}}", ""));
        string output = Value(request.Arguments, "--output");
        if (request.Command == "run")
        {
            RunCount++;
            if (FailNextRun)
            {
                FailNextRun = false;
                return Task.FromResult(new PixelLabProcessResult(2, "", "Fake transport timed out; retry is safe."));
            }
            int count = int.Parse(Value(request.Arguments, "--candidates"));
            _lastOutput = output;
            Directory.CreateDirectory(output);
            string controls = Path.Combine(output, "controls");
            Directory.CreateDirectory(controls);
            File.WriteAllText(Path.Combine(controls, "visual-brief.json"),
                "{\"contractVersion\":\"test-fake\"}");
            File.WriteAllBytes(Path.Combine(controls, "semantic-control.png"), OnePixelPng);
            File.WriteAllBytes(Path.Combine(controls, "protected-mask.png"), OnePixelPng);
            File.WriteAllText(Path.Combine(output, "run-plan.json"), JsonSerializer.Serialize(new
            {
                candidates = Enumerable.Range(0, count).Select(index => new { candidateIndex = index, seed = index + 1 })
            }));
            for (int index = 0; index < count; index++)
            {
                string candidate = Path.Combine(output, "candidates", $"candidate-{index:D3}");
                Directory.CreateDirectory(candidate);
                File.WriteAllBytes(Path.Combine(candidate, "candidate.png"), OnePixelPng);
                File.WriteAllText(Path.Combine(candidate, "validation.json"),
                    """{"structurallyValid":true,"eligibleForApproval":true,"resultingState":"generated","failures":[]}""");
                File.WriteAllText(Path.Combine(candidate, "generation-manifest.json"),
                    JsonSerializer.Serialize(new
                    {
                        provider = "test-fake",
                        remote = new { cacheHit = index == 1, usage = (object?)null },
                    }));
            }
            return Task.FromResult(new PixelLabProcessResult(0,
                $"{{\"submissions\":{Math.Max(0, count - 1)}}}", ""));
        }

        int candidateIndex = int.Parse(Value(request.Arguments, "--candidate"));
        string candidateDirectory = Path.Combine(output, "candidates", $"candidate-{candidateIndex:D3}");
        string state = request.Command == "approve" ? "human-approved" : "rejected";
        File.WriteAllText(Path.Combine(candidateDirectory, "approval.json"),
            JsonSerializer.Serialize(new { currentState = state, decisions = new[] { new { actor = Value(request.Arguments, "--actor") } } }));
        return Task.FromResult(new PixelLabProcessResult(0,
            $"{{\"command\":\"{request.Command}\",\"currentState\":\"{state}\"}}", ""));
    }

    public void ChangeCandidate(string jobId)
    {
        if (_lastOutput is null || !string.Equals(Path.GetFileName(_lastOutput), jobId,
            StringComparison.Ordinal)) throw new InvalidOperationException("The requested fake job was not generated.");
        File.WriteAllBytes(Path.Combine(_lastOutput, "candidates", "candidate-000", "candidate.png"),
            [.. OnePixelPng, 0]);
    }

    private static string Value(IReadOnlyList<string> arguments, string name)
    {
        for (int index = 0; index < arguments.Count - 1; index++)
            if (arguments[index] == name) return arguments[index + 1];
        throw new InvalidOperationException($"Missing fake argument {name}.");
    }

    private static readonly byte[] OnePixelPng = Convert.FromBase64String(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=");
}
