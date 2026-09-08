namespace MapGen.Api.PixelLab;

public sealed record CreatePixelLabJobRequest(
    string WorldJobId,
    int CandidateCount = 3,
    int CandidateBudget = 0,
    string Mode = "offline",
    bool EnableLiveCalls = false,
    bool ConfirmCreditSpend = false);

public sealed record PixelLabDecisionRequest(string Actor, string Reason);

public sealed record PixelLabEvaluationScores(
    int ShorelineFidelity,
    int TraversabilityCues,
    int StartsAndResources,
    int VisualCohesion,
    int GameplayReadability);

public sealed record PixelLabEvaluationRequest(
    string Reviewer,
    string Rationale,
    string Verdict,
    PixelLabEvaluationScores Scores);

public sealed record PixelLabEvidenceObservation(
    string Status,
    decimal? Value,
    string? Unit);

public sealed record PixelLabEvaluationReview(
    string Reviewer,
    string Rationale,
    string Verdict,
    PixelLabEvaluationScores Scores,
    DateTimeOffset RecordedAtUtc,
    string BoundEvidenceDigest,
    bool Current);

public sealed record PixelLabEvaluationCandidate(
    int CandidateIndex,
    long CandidateSeed,
    string State,
    bool StructurallyValid,
    bool EligibleForEvaluation,
    string EvidenceDigest,
    IReadOnlyDictionary<string, string> ArtifactDigests,
    IReadOnlyDictionary<string, string> ArtifactUrls,
    string Provider,
    PixelLabEvidenceObservation Cost,
    PixelLabEvidenceObservation Latency,
    IReadOnlyList<string> ValidationFailures,
    IReadOnlyList<PixelLabEvaluationReview> Reviews);

public sealed record PixelLabEvaluationBundle(
    int Version,
    string JobId,
    string WorldJobId,
    long WorldSeed,
    IReadOnlyList<PixelLabEvaluationCandidate> Candidates);

public sealed record PixelLabReadiness(
    bool Available,
    bool LiveConfigured,
    string Mode,
    decimal? Balance,
    string? BalanceCurrency,
    string? Message);

public sealed record PixelLabCandidate(
    int CandidateIndex,
    long Seed,
    string State,
    bool StructurallyValid,
    bool EligibleForApproval,
    bool CacheHit,
    IReadOnlyList<string> Failures,
    string? ImageUrl);

public sealed record PixelLabJobSnapshot(
    string JobId,
    string WorldJobId,
    string Status,
    string Stage,
    int Pct,
    string Mode,
    int CandidateBudget,
    int Submissions,
    int CacheHits,
    DateTimeOffset SubmittedAtUtc,
    DateTimeOffset? CompletedAtUtc,
    string? Error,
    IReadOnlyList<PixelLabCandidate> Candidates);
