namespace MapGen.Api.PixelLab;

public sealed record CreatePixelLabJobRequest(
    string WorldJobId,
    int CandidateCount = 3,
    int CandidateBudget = 0,
    string Mode = "offline",
    bool EnableLiveCalls = false,
    bool ConfirmCreditSpend = false);

public sealed record PixelLabDecisionRequest(string Actor, string Reason);

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

