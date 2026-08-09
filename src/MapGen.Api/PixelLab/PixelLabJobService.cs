using System.Collections.Concurrent;
using System.Text.Json;
using MapGen.Application.WorldGeneration;

namespace MapGen.Api.PixelLab;

public interface IPixelLabJobService
{
    PixelLabReadiness Readiness();
    Task<PixelLabReadiness> RefreshBalanceAsync(CancellationToken cancellationToken);
    Task<PixelLabJobSnapshot> SubmitAsync(CreatePixelLabJobRequest request, CancellationToken cancellationToken);
    PixelLabJobSnapshot? Find(string jobId);
    Task<PixelLabJobSnapshot?> RetryAsync(string jobId, CancellationToken cancellationToken);
    Task<PixelLabJobSnapshot?> DecideAsync(string jobId, int candidateIndex, string decision,
        PixelLabDecisionRequest request, CancellationToken cancellationToken);
    string? ResolveCandidateImage(string jobId, int candidateIndex);
}

internal sealed class PixelLabJobRecord
{
    public required string JobId { get; init; }
    public required CreatePixelLabJobRequest Request { get; init; }
    public required string GoldenJobId { get; init; }
    public required string RunRoot { get; init; }
    public required DateTimeOffset SubmittedAtUtc { get; init; }
    public string Status { get; set; } = "queued";
    public string Stage { get; set; } = "queued";
    public int Pct { get; set; }
    public int Submissions { get; set; }
    public int CacheHits { get; set; }
    public DateTimeOffset? CompletedAtUtc { get; set; }
    public string? Error { get; set; }
    public List<PixelLabCandidate> Candidates { get; set; } = [];
}

public sealed class PixelLabJobService(
    PixelLabOptions options,
    WorldJobRegistry worlds,
    IPixelLabProcessExecutor executor,
    TimeProvider clock,
    ILogger<PixelLabJobService> logger) : IPixelLabJobService
{
    private readonly ConcurrentDictionary<string, PixelLabJobRecord> _jobs = LoadExisting(options);
    private PixelLabReadiness? _lastReadiness;

    public PixelLabReadiness Readiness()
    {
        if (options.UseFakeTransport)
            return new PixelLabReadiness(true, false, "development-fake", 999, "fake credits",
                "Development fake transport: no PixelLab request or credit spend is possible.");
        bool available = File.Exists(Path.Combine(options.RepositoryRoot, options.OrchestratorPath));
        bool liveConfigured = !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
            options.TokenEnvironmentVariable));
        if (_lastReadiness is not null && _lastReadiness.LiveConfigured == liveConfigured) return _lastReadiness;
        return new PixelLabReadiness(available, liveConfigured, "offline", null, null,
            liveConfigured ? "PixelLab is configured; generation still requires both live confirmations."
                : "Offline/fake mode is ready. Live balance is unavailable until the server token is configured.");
    }

    public async Task<PixelLabReadiness> RefreshBalanceAsync(CancellationToken cancellationToken)
    {
        PixelLabReadiness current = Readiness();
        if (!current.LiveConfigured)
            throw new InvalidOperationException("The server token is not configured; no balance request was made.");
        PixelLabProcessResult result = await executor.ExecuteAsync(
            new PixelLabProcessRequest("balance", ["--enable-live-calls"]), cancellationToken);
        if (result.ExitCode != 0) throw new InvalidOperationException(SafeError(result));
        using JsonDocument document = JsonDocument.Parse(result.StandardOutput.Trim());
        JsonElement balanceObject = document.RootElement.GetProperty("balance");
        decimal? amount = FindDecimal(balanceObject, "balance", "amount", "credits");
        string? currency = FindString(balanceObject, "currency", "unit");
        _lastReadiness = current with
        {
            Mode = "live-readiness",
            Balance = amount,
            BalanceCurrency = currency,
            Message = amount is null ? "PixelLab responded, but did not expose a numeric balance."
                : "Balance refreshed with a read-only request; no generation was submitted.",
        };
        return _lastReadiness;
    }

    public Task<PixelLabJobSnapshot> SubmitAsync(CreatePixelLabJobRequest request, CancellationToken cancellationToken)
    {
        ValidateRequest(request);
        WorldJob world = worlds.Find(request.WorldJobId)
            ?? throw new KeyNotFoundException($"World job '{request.WorldJobId}' was not found.");
        if (!worlds.HasSucceeded(world))
        {
            throw new InvalidOperationException("The world job must succeed before presentation candidates can run.");
        }

        string jobId = Guid.NewGuid().ToString();
        string runRoot = Path.Combine(options.RunsRoot, jobId);
        Directory.CreateDirectory(runRoot);
        var record = new PixelLabJobRecord
        {
            JobId = jobId,
            Request = request,
            GoldenJobId = world.GoldenJobId,
            RunRoot = runRoot,
            SubmittedAtUtc = clock.GetUtcNow(),
        };
        _jobs[jobId] = record;
        Persist(record);
        _ = RunAsync(record, CancellationToken.None);
        return Task.FromResult(ToSnapshot(record));
    }

    public PixelLabJobSnapshot? Find(string jobId)
        => _jobs.TryGetValue(jobId, out var record) ? RefreshAndSnapshot(record) : null;

    public async Task<PixelLabJobSnapshot?> RetryAsync(string jobId, CancellationToken cancellationToken)
    {
        if (!_jobs.TryGetValue(jobId, out var record)) return null;
        lock (record)
        {
            if (record.Status is "queued" or "running") return ToSnapshot(record);
            record.Status = "queued";
            record.Stage = "retrying";
            record.Pct = 0;
            record.Error = null;
            record.CompletedAtUtc = null;
            Persist(record);
        }
        await RunAsync(record, cancellationToken);
        return ToSnapshot(record);
    }

    public async Task<PixelLabJobSnapshot?> DecideAsync(string jobId, int candidateIndex,
        string decision, PixelLabDecisionRequest request, CancellationToken cancellationToken)
    {
        if (!_jobs.TryGetValue(jobId, out var record)) return null;
        if (string.IsNullOrWhiteSpace(request.Actor) || string.IsNullOrWhiteSpace(request.Reason))
            throw new ArgumentException("Actor and reason are required for a human decision.");

        var result = await executor.ExecuteAsync(new PixelLabProcessRequest(decision,
        [
            "--output", record.RunRoot,
            "--cache", Path.Combine(options.RunsRoot, "cache"),
            "--candidate", candidateIndex.ToString(),
            "--actor", request.Actor.Trim(),
            "--reason", request.Reason.Trim(),
        ]), cancellationToken);
        if (result.ExitCode != 0) throw new InvalidOperationException(SafeError(result));
        RefreshCandidates(record);
        Persist(record);
        return ToSnapshot(record);
    }

    public string? ResolveCandidateImage(string jobId, int candidateIndex)
    {
        if (!_jobs.TryGetValue(jobId, out var record)) return null;
        PixelLabCandidate? candidate = RefreshAndSnapshot(record).Candidates
            .SingleOrDefault(item => item.CandidateIndex == candidateIndex);
        if (candidate?.State is not ("generated" or "human-approved")) return null;
        string path = Path.Combine(record.RunRoot, "candidates", $"candidate-{candidateIndex:D3}", "candidate.png");
        return File.Exists(path) ? path : null;
    }

    private async Task RunAsync(PixelLabJobRecord record, CancellationToken cancellationToken)
    {
        lock (record) { record.Status = "running"; record.Stage = "building-controls"; record.Pct = 10; }
        string payload = Path.Combine(options.GoldenFixturesRoot, record.GoldenJobId,
            $"{record.GoldenJobId}.worldpayload");
        var args = new List<string>
        {
            "--input", payload,
            "--output", record.RunRoot,
            "--cache", Path.Combine(options.RunsRoot, "cache"),
            "--candidates", record.Request.CandidateCount.ToString(),
            "--candidate-budget", record.Request.CandidateBudget.ToString(),
            "--mode", record.Request.Mode,
        };
        if (record.Request.EnableLiveCalls) args.Add("--enable-live-calls");
        if (record.Request.ConfirmCreditSpend) args.Add("--confirm-credit-spend");

        try
        {
            lock (record) { record.Stage = "generating-candidates"; record.Pct = 45; }
            PixelLabProcessResult result = await executor.ExecuteAsync(
                new PixelLabProcessRequest("run", args), cancellationToken);
            if (result.ExitCode != 0) throw new InvalidOperationException(SafeError(result));
            using JsonDocument summary = JsonDocument.Parse(result.StandardOutput.Trim());
            lock (record)
            {
                record.Submissions = summary.RootElement.TryGetProperty("submissions", out var submissions)
                    ? submissions.GetInt32() : 0;
                record.Status = "succeeded";
                record.Stage = "awaiting-approval";
                record.Pct = 100;
                record.CompletedAtUtc = clock.GetUtcNow();
                RefreshCandidates(record);
                Persist(record);
            }
        }
        catch (Exception error)
        {
            logger.LogWarning(error, "PixelLab job {JobId} failed", record.JobId);
            lock (record)
            {
                record.Status = "failed";
                record.Stage = "failed";
                record.Pct = 100;
                record.CompletedAtUtc = clock.GetUtcNow();
                record.Error = error.Message;
                Persist(record);
            }
        }
    }

    private PixelLabJobSnapshot RefreshAndSnapshot(PixelLabJobRecord record)
    {
        if (record.Status == "succeeded") RefreshCandidates(record);
        return ToSnapshot(record);
    }

    private void RefreshCandidates(PixelLabJobRecord record)
    {
        string planPath = Path.Combine(record.RunRoot, "run-plan.json");
        if (!File.Exists(planPath)) return;
        using JsonDocument plan = JsonDocument.Parse(File.ReadAllText(planPath));
        var candidates = new List<PixelLabCandidate>();
        int cacheHits = 0;
        foreach (JsonElement entry in plan.RootElement.GetProperty("candidates").EnumerateArray())
        {
            int index = entry.GetProperty("candidateIndex").GetInt32();
            long seed = entry.GetProperty("seed").GetInt64();
            string directory = Path.Combine(record.RunRoot, "candidates", $"candidate-{index:D3}");
            JsonElement validation = ReadObject(Path.Combine(directory, "validation.json"));
            JsonElement approval = ReadObject(Path.Combine(directory, "approval.json"));
            JsonElement manifest = ReadObject(Path.Combine(directory, "generation-manifest.json"));
            bool valid = GetBool(validation, "structurallyValid");
            bool eligible = GetBool(validation, "eligibleForApproval");
            string state = GetString(approval, "currentState")
                ?? GetString(validation, "resultingState") ?? "planned";
            bool cacheHit = manifest.ValueKind == JsonValueKind.Object
                && manifest.TryGetProperty("remote", out var remote) && GetBool(remote, "cacheHit");
            if (cacheHit) cacheHits++;
            string[] failures = validation.ValueKind == JsonValueKind.Object
                && validation.TryGetProperty("failures", out var failuresElement)
                ? failuresElement.EnumerateArray().Select(item => item.GetString() ?? "Validation failed.").ToArray()
                : [];
            bool hasImage = File.Exists(Path.Combine(directory, "candidate.png"));
            candidates.Add(new PixelLabCandidate(index, seed, state, valid, eligible, cacheHit,
                failures, hasImage ? $"/api/v1/pixellab/jobs/{record.JobId}/candidates/{index}/image" : null));
        }
        record.Candidates = candidates;
        record.CacheHits = cacheHits;
        Persist(record);
    }

    private static JsonElement ReadObject(string path)
    {
        if (!File.Exists(path)) return default;
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        return document.RootElement.Clone();
    }
    private static bool GetBool(JsonElement element, string name) => element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.True;
    private static string? GetString(JsonElement element, string name) => element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static decimal? FindDecimal(JsonElement element, params string[] names)
    {
        foreach (string name in names)
            if (element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var value)
                && value.ValueKind == JsonValueKind.Number && value.TryGetDecimal(out decimal amount)) return amount;
        return null;
    }
    private static string? FindString(JsonElement element, params string[] names)
    {
        foreach (string name in names)
            if (element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var value)
                && value.ValueKind == JsonValueKind.String) return value.GetString();
        return null;
    }

    private static void ValidateRequest(CreatePixelLabJobRequest request)
    {
        if (request.CandidateCount is < 1 or > 4) throw new ArgumentOutOfRangeException(nameof(request.CandidateCount), "Candidate count must be between 1 and 4.");
        if (request.CandidateBudget < 0 || request.CandidateBudget > request.CandidateCount) throw new ArgumentOutOfRangeException(nameof(request.CandidateBudget), "Candidate budget must be between zero and the candidate count.");
        if (request.Mode is not ("offline" or "live")) throw new ArgumentException("Mode must be offline or live.");
        if (request.Mode == "live" && (!request.EnableLiveCalls || !request.ConfirmCreditSpend))
            throw new ArgumentException("Live generation requires both explicit live-call and credit-spend confirmations.");
        if (request.Mode == "offline" && (request.EnableLiveCalls || request.ConfirmCreditSpend))
            throw new ArgumentException("Live confirmations are not valid in offline mode.");
    }

    private static string SafeError(PixelLabProcessResult result)
    {
        string error = string.IsNullOrWhiteSpace(result.StandardError)
            ? $"PixelLab worker exited with code {result.ExitCode}." : result.StandardError.Trim();
        return error.Length <= 1000 ? error : error[..1000];
    }

    private static PixelLabJobSnapshot ToSnapshot(PixelLabJobRecord record) => new(
        record.JobId, record.Request.WorldJobId, record.Status, record.Stage, record.Pct,
        record.Request.Mode, record.Request.CandidateBudget, record.Submissions, record.CacheHits,
        record.SubmittedAtUtc, record.CompletedAtUtc, record.Error, record.Candidates.ToArray());

    private static ConcurrentDictionary<string, PixelLabJobRecord> LoadExisting(PixelLabOptions options)
    {
        var jobs = new ConcurrentDictionary<string, PixelLabJobRecord>(StringComparer.Ordinal);
        if (!Directory.Exists(options.RunsRoot)) return jobs;
        foreach (string path in Directory.EnumerateFiles(options.RunsRoot, "job.json", SearchOption.AllDirectories))
        {
            try
            {
                PixelLabJobRecord? record = JsonSerializer.Deserialize<PixelLabJobRecord>(File.ReadAllText(path));
                if (record is not null) jobs[record.JobId] = record;
            }
            catch (Exception error) when (error is IOException or JsonException)
            {
                // One damaged job must not hide healthy runs; its directory remains as evidence.
            }
        }
        return jobs;
    }

    private static void Persist(PixelLabJobRecord record)
    {
        Directory.CreateDirectory(record.RunRoot);
        string destination = Path.Combine(record.RunRoot, "job.json");
        string temporary = destination + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(record));
        File.Move(temporary, destination, true);
    }
}
