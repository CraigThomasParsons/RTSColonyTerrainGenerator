using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace MapGen.Api.PixelLab;

internal static class PixelLabEvaluation
{
    private const int ContractVersion = 1;
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private sealed record StoredReview(
        string Reviewer,
        string Rationale,
        string Verdict,
        PixelLabEvaluationScores Scores,
        DateTimeOffset RecordedAtUtc,
        string BoundEvidenceDigest);

    private sealed record StoredEvaluation(int Version, IReadOnlyList<StoredReview> Reviews);

    public static PixelLabEvaluationBundle BuildBundle(PixelLabJobRecord record)
    {
        var candidates = record.Candidates
            .Select(candidate => BuildCandidate(record, candidate))
            .ToArray();
        return new PixelLabEvaluationBundle(
            ContractVersion, record.JobId, record.Request.WorldJobId, record.WorldSeed, candidates);
    }

    public static PixelLabEvaluationCandidate Record(PixelLabJobRecord record, int candidateIndex,
        PixelLabEvaluationRequest request, DateTimeOffset recordedAtUtc)
    {
        ValidateRequest(request);
        PixelLabCandidate candidate = record.Candidates.SingleOrDefault(item =>
            item.CandidateIndex == candidateIndex)
            ?? throw new ArgumentException($"Candidate {candidateIndex} was not found.");
        PixelLabEvaluationCandidate evidence = BuildCandidate(record, candidate);
        if (!evidence.EligibleForEvaluation)
            throw new InvalidOperationException("Only structurally valid candidates with complete evidence can be evaluated.");

        string evaluationPath = EvaluationPath(record, candidateIndex);
        StoredEvaluation stored = ReadStored(evaluationPath);
        var replacement = new StoredReview(
            request.Reviewer.Trim(), request.Rationale.Trim(), request.Verdict,
            request.Scores, recordedAtUtc, evidence.EvidenceDigest);
        StoredReview[] reviews = stored.Reviews
            .Where(review => !string.Equals(review.Reviewer, replacement.Reviewer,
                StringComparison.OrdinalIgnoreCase))
            .Append(replacement)
            .OrderBy(review => review.Reviewer, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        WriteAtomically(evaluationPath, new StoredEvaluation(ContractVersion, reviews));
        return BuildCandidate(record, candidate);
    }

    public static PixelLabEvidenceArtifact? ResolveArtifact(PixelLabJobRecord record,
        int candidateIndex, string artifact)
    {
        string candidateRoot = CandidateRoot(record, candidateIndex);
        (string Path, string ContentType)? resolved = artifact switch
        {
            "semantic-control" => (Path.Combine(record.RunRoot, "controls", "semantic-control.png"), "image/png"),
            "protected-mask" => (Path.Combine(record.RunRoot, "controls", "protected-mask.png"), "image/png"),
            "validation" => (Path.Combine(candidateRoot, "validation.json"), "application/json"),
            "provenance" => (Path.Combine(candidateRoot, "generation-manifest.json"), "application/json"),
            _ => null,
        };
        if (resolved is null || !File.Exists(resolved.Value.Path)) return null;
        return new PixelLabEvidenceArtifact(resolved.Value.Path, resolved.Value.ContentType);
    }

    private static PixelLabEvaluationCandidate BuildCandidate(PixelLabJobRecord record,
        PixelLabCandidate candidate)
    {
        string candidateRoot = CandidateRoot(record, candidate.CandidateIndex);
        var paths = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["source"] = Path.Combine(record.RunRoot, "controls", "visual-brief.json"),
            ["semantic_control"] = Path.Combine(record.RunRoot, "controls", "semantic-control.png"),
            ["protected_mask"] = Path.Combine(record.RunRoot, "controls", "protected-mask.png"),
            ["candidate"] = Path.Combine(candidateRoot, "candidate.png"),
            ["validation"] = Path.Combine(candidateRoot, "validation.json"),
            ["approval"] = Path.Combine(candidateRoot, "approval.json"),
            ["provenance"] = Path.Combine(candidateRoot, "generation-manifest.json"),
        };
        Dictionary<string, string> digests = paths
            .Where(pair => File.Exists(pair.Value))
            .ToDictionary(pair => pair.Key, pair => Sha256File(pair.Value), StringComparer.Ordinal);
        string evidenceDigest = EvidenceDigest(record, candidate, digests);
        JsonElement manifest = ReadObject(paths["provenance"]);
        string provider = ReadProvider(manifest);
        PixelLabEvidenceObservation cost = ReadCost(manifest);
        PixelLabEvidenceObservation latency = ReadLatency(manifest);
        var urls = new Dictionary<string, string>(StringComparer.Ordinal);
        AddUrlIfPresent(urls, paths, "semantic_control", record.JobId, candidate.CandidateIndex, "semantic-control");
        AddUrlIfPresent(urls, paths, "protected_mask", record.JobId, candidate.CandidateIndex, "protected-mask");
        AddUrlIfPresent(urls, paths, "validation", record.JobId, candidate.CandidateIndex, "validation");
        AddUrlIfPresent(urls, paths, "provenance", record.JobId, candidate.CandidateIndex, "provenance");
        if (paths.TryGetValue("candidate", out string? image) && File.Exists(image))
            urls["candidate"] = $"/pixellab/jobs/{record.JobId}/candidates/{candidate.CandidateIndex}/image";

        bool complete = new[] { "source", "semantic_control", "protected_mask", "candidate", "validation", "approval", "provenance" }
            .All(digests.ContainsKey);
        StoredEvaluation stored = ReadStored(EvaluationPath(record, candidate.CandidateIndex));
        PixelLabEvaluationReview[] reviews = stored.Reviews.Select(review => new PixelLabEvaluationReview(
            review.Reviewer, review.Rationale, review.Verdict, review.Scores, review.RecordedAtUtc,
            review.BoundEvidenceDigest, review.BoundEvidenceDigest == evidenceDigest)).ToArray();
        return new PixelLabEvaluationCandidate(
            candidate.CandidateIndex, candidate.Seed, candidate.State, candidate.StructurallyValid,
            candidate.State == "human-approved" && candidate.StructurallyValid
                && candidate.EligibleForApproval && complete,
            evidenceDigest, digests, urls, provider, cost, latency, candidate.Failures, reviews);
    }

    private static void ValidateRequest(PixelLabEvaluationRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Reviewer) || string.IsNullOrWhiteSpace(request.Rationale))
            throw new ArgumentException("Reviewer and rationale are required for an evaluation.");
        if (request.Verdict is not ("accept" or "reject"))
            throw new ArgumentException("Evaluation verdict must be accept or reject.");
        int[] scores = [request.Scores.ShorelineFidelity, request.Scores.TraversabilityCues,
            request.Scores.StartsAndResources, request.Scores.VisualCohesion,
            request.Scores.GameplayReadability];
        if (scores.Any(score => score is < 1 or > 5))
            throw new ArgumentOutOfRangeException(nameof(request.Scores), "Every evaluation score must be between 1 and 5.");
    }

    private static string EvidenceDigest(PixelLabJobRecord record, PixelLabCandidate candidate,
        IReadOnlyDictionary<string, string> digests)
    {
        var material = new StringBuilder()
            .Append(ContractVersion).Append('\n')
            .Append(record.JobId).Append('\n')
            .Append(record.Request.WorldJobId).Append('\n')
            .Append(record.WorldSeed).Append('\n')
            .Append(candidate.CandidateIndex).Append('\n');
        foreach ((string name, string digest) in digests.OrderBy(pair => pair.Key, StringComparer.Ordinal))
            material.Append(name).Append('=').Append(digest).Append('\n');
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(material.ToString()))).ToLowerInvariant();
    }

    private static string Sha256File(string path) =>
        Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

    private static string CandidateRoot(PixelLabJobRecord record, int index) =>
        Path.Combine(record.RunRoot, "candidates", $"candidate-{index:D3}");

    private static string EvaluationPath(PixelLabJobRecord record, int index) =>
        Path.Combine(CandidateRoot(record, index), "evaluation.json");

    private static StoredEvaluation ReadStored(string path)
    {
        if (!File.Exists(path)) return new StoredEvaluation(ContractVersion, []);
        try
        {
            return JsonSerializer.Deserialize<StoredEvaluation>(File.ReadAllText(path))
                ?? new StoredEvaluation(ContractVersion, []);
        }
        catch (JsonException)
        {
            return new StoredEvaluation(ContractVersion, []);
        }
    }

    private static void WriteAtomically(string destination, StoredEvaluation evaluation)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
        string temporary = destination + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(evaluation, JsonOptions));
        File.Move(temporary, destination, true);
    }

    private static JsonElement ReadObject(string path)
    {
        if (!File.Exists(path)) return default;
        using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path));
        return document.RootElement.Clone();
    }

    private static string ReadProvider(JsonElement manifest)
    {
        if (manifest.ValueKind != JsonValueKind.Object) return "not-observed";
        if (manifest.TryGetProperty("provider", out JsonElement provider)
            && provider.ValueKind == JsonValueKind.String) return provider.GetString() ?? "not-observed";
        return manifest.TryGetProperty("endpoint", out JsonElement endpoint)
            && endpoint.ValueKind == JsonValueKind.String ? "pixellab" : "not-observed";
    }

    private static PixelLabEvidenceObservation ReadCost(JsonElement manifest)
    {
        if (manifest.ValueKind == JsonValueKind.Object
            && manifest.TryGetProperty("remote", out JsonElement remote)
            && remote.TryGetProperty("usage", out JsonElement usage)
            && usage.ValueKind == JsonValueKind.Object)
        {
            foreach (string name in new[] { "usd", "amount", "credits" })
                if (usage.TryGetProperty(name, out JsonElement value) && value.TryGetDecimal(out decimal amount))
                    return new PixelLabEvidenceObservation("observed", amount, name == "usd" ? "USD" : name);
        }
        return new PixelLabEvidenceObservation("not-observed", null, null);
    }

    private static PixelLabEvidenceObservation ReadLatency(JsonElement manifest)
    {
        if (manifest.ValueKind == JsonValueKind.Object
            && manifest.TryGetProperty("remote", out JsonElement remote)
            && remote.TryGetProperty("latencyMs", out JsonElement latency)
            && latency.TryGetDecimal(out decimal milliseconds))
            return new PixelLabEvidenceObservation("observed", milliseconds, "ms");
        return new PixelLabEvidenceObservation("not-observed", null, null);
    }

    private static void AddUrlIfPresent(IDictionary<string, string> urls,
        IReadOnlyDictionary<string, string> paths, string key, string jobId, int candidateIndex,
        string artifact)
    {
        if (paths.TryGetValue(key, out string? path) && File.Exists(path))
            urls[key] = $"/pixellab/jobs/{jobId}/candidates/{candidateIndex}/evidence/{artifact}";
    }
}
