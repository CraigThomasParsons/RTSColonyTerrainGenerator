using Xunit;

namespace MapGen.CompatibilityTests;

/// <summary>
/// Gate 7 harness: legacy stage output versus replacement output, compared at the logical
/// level (tools/artifact_hash). Phase 0 (M1) establishes the baseline and proves the harness
/// end to end; the stage-replacement comparisons arrive with each migration slice.
///
/// The comparison recipe a migration slice fills in:
///   1. take a golden job's input artifact (e.g. its .heightmap);
///   2. run the replacement stage (e.g. the verified C# Tiler) on it;
///   3. logical-hash the output and assert it equals the golden manifest hash.
/// For binary artifacts the C# and Python hashes are identical by construction, so a slice
/// only needs step 2 — the plumbing below already does 1 and 3.
/// </summary>
public class CompatibilityHarnessTest
{
    [Fact]
    public void Golden_fixtures_are_present()
    {
        foreach (var job in GoldenFixtures.JobIds)
        {
            Assert.True(Directory.Exists(GoldenFixtures.JobDir(job)), $"missing golden fixture dir for {job}");
            Assert.True(File.Exists(GoldenFixtures.ArtifactPath(job, ".heightmap")), $"missing .heightmap for {job}");
            Assert.True(File.Exists(GoldenFixtures.ArtifactPath(job, ".maptiles")), $"missing .maptiles for {job}");
        }
    }

    [Theory]
    [InlineData("43860dcf-6469-42a7-9843-4e33abeacfac")]
    [InlineData("3c96b74c-6f86-4d27-a0ca-c567f385ae8e")]
    [InlineData("0860a05a-a410-4cc2-987d-a48a4cd120c7")]
    public void Csharp_hash_agrees_with_recorded_manifest_hash(string job)
    {
        // Proves: fixtures are locatable, the manifest parses, and C# binary hashing agrees
        // with the Python tool that recorded the golden baseline. This is the parity substrate
        // Epic 1's Tiler comparison stands on.
        var recorded = GoldenFixtures.ManifestHash(job, $"MapGenerator/Tiler/outbox/{job}.maptiles");
        var computed = GoldenFixtures.BinaryLogicalHash(GoldenFixtures.ArtifactPath(job, ".maptiles"));

        Assert.Equal(recorded, computed);
    }

    [Fact(Skip = "Epic 1 (M3): run the verified C# Tiler on each golden .heightmap and assert its .maptiles logical hash equals the manifest hash asserted above.")]
    public void Replacement_tiler_matches_legacy_on_golden_jobs()
    {
    }
}
