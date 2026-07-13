using Xunit;

namespace MapGen.CompatibilityTests;

/// <summary>
/// Gate 7 harness seat: legacy stage output versus replacement output, compared at
/// the logical level after normalizing non-contractual metadata (timestamps, temp paths).
///
/// The harness fills in as stages migrate:
///  1. run the legacy stage on a golden job fixture;
///  2. run the C# replacement on the same fixture;
///  3. normalize, diff, and store a human-readable report on failure.
/// </summary>
public class CompatibilityHarnessTest
{
    [Fact(Skip = "No migrated stage yet — Epic 1 (cell-to-tile) adds the first legacy-vs-C# comparison against the Tiler.")]
    public void Legacy_and_replacement_outputs_agree_on_golden_jobs()
    {
    }
}
