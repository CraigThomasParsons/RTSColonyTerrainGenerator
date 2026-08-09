using MapGen.Api.Replay;

namespace MapGen.Api.Tests;

/// <summary>
/// The fixture reader, against the real Golden Jobs on disk. The seam under test is
/// <see cref="GoldenJobFileSource.Read"/>: what the on-disk artifacts become once parsed.
///
/// These are the artifacts the legacy pipeline actually wrote, so the assertions are about
/// the shape and bounds the reader guarantees, never about a hand-recomputed value.
/// </summary>
public class GoldenJobFileSourceTests
{
    private const string JobId = "43860dcf-6469-42a7-9843-4e33abeacfac";

    private static GoldenJobFileSource Source() => new(FixturesRoot());

    [Fact]
    public void Every_golden_job_carries_a_canopy_read_from_its_worldpayload()
    {
        var source = Source();

        // The three pinned jobs each have a captured `.worldpayload`; a job whose canopy
        // came back empty would mean the reader silently found nothing, which is exactly
        // the two-green-squares bug this slice exists to fix.
        Assert.NotEmpty(source.JobIds);
        foreach (string jobId in source.JobIds)
        {
            Assert.NotEmpty(source.Read(jobId).Trees);
        }
    }

    [Fact]
    public void Tree_placements_are_tile_x_y_inside_the_tile_grid()
    {
        var artifacts = Source().Read(JobId);

        foreach (var tree in artifacts.Trees)
        {
            Assert.InRange(tree.X, 0, artifacts.TileWidth - 1);
            Assert.InRange(tree.Y, 0, artifacts.TileHeight - 1);
        }
    }

    [Fact]
    public void No_two_trees_occupy_the_same_tile()
    {
        // One `.worldpayload` tile entry carries at most one canopy position, so a repeat
        // would mean the reader emitted a tile twice.
        var artifacts = Source().Read(JobId);

        Assert.Equal(
            artifacts.Trees.Count,
            artifacts.Trees.Select(tree => (tree.X, tree.Y)).Distinct().Count());
    }

    [Fact]
    public void A_job_without_a_worldpayload_replays_with_an_empty_canopy()
    {
        // TreePlanter runs downstream of the artifacts a Golden Job is discovered by, so its
        // artifact is optional: a fixture captured before this slice must still replay, as a
        // map with no forest rather than a failed job.
        //
        // Only the files Read() opens are copied — .heightmap and .weather are unused here.
        string root = Path.Combine(Path.GetTempPath(), $"mapgen-golden-{Guid.NewGuid():N}");
        string jobDirectory = Path.Combine(root, JobId);
        Directory.CreateDirectory(jobDirectory);

        try
        {
            CopyReadInputs(jobDirectory);

            Assert.Empty(new GoldenJobFileSource(root).Read(JobId).Trees);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void A_planted_tile_without_coordinates_is_malformed_not_an_origin_tree()
    {
        // Missing x/y must not default to (0, 0): that plants a tree at the origin and
        // disagrees with every other malformed-fixture path, which throws InvalidDataException.
        string root = Path.Combine(Path.GetTempPath(), $"mapgen-golden-{Guid.NewGuid():N}");
        string jobDirectory = Path.Combine(root, JobId);
        Directory.CreateDirectory(jobDirectory);

        try
        {
            CopyReadInputs(jobDirectory);
            File.WriteAllText(
                Path.Combine(jobDirectory, $"{JobId}.worldpayload"),
                """
                {
                  "tiles": [
                    {
                      "decorations": [ { "type": "tree", "variety": "oak" } ]
                    }
                  ]
                }
                """);

            var error = Assert.Throws<InvalidDataException>(
                () => new GoldenJobFileSource(root).Read(JobId));

            Assert.Contains("numeric", error.Message, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("'x'", error.Message, StringComparison.Ordinal);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    // The host's own answer to "which fixtures are we replaying?", asked from the test
    // assembly's bin instead of a content root. Re-deriving it here would let this test pass
    // against a directory the running API would never read.
    private static string FixturesRoot()
        => GoldenFixtures.ResolveRoot(configuredRoot: null, AppContext.BaseDirectory);

    /// <summary>
    /// The three artifacts <see cref="GoldenJobFileSource.Read"/> always opens, for temp
    /// fixtures that only vary the optional canopy.
    /// </summary>
    private static void CopyReadInputs(string jobDirectory)
    {
        string sourceDirectory = Path.Combine(FixturesRoot(), JobId);
        foreach (string name in new[]
                 {
                     $"{JobId}.maptiles",
                     $"{JobId}.playable.json",
                     "input.job.json",
                 })
        {
            File.Copy(Path.Combine(sourceDirectory, name), Path.Combine(jobDirectory, name));
        }
    }
}
