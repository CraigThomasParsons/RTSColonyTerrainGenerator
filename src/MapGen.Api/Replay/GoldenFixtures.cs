namespace MapGen.Api.Replay;

/// <summary>
/// Where the read-only Golden Job fixtures live. Configuration wins; otherwise walk up to the
/// repository marker, so a host — or a test assembly running out of its own <c>bin</c> —
/// finds them from any working directory.
///
/// One statement of this, next to the <see cref="GoldenJobFileSource"/> it feeds: a second
/// copy of the walk is a second answer to "which fixtures are we replaying?".
/// </summary>
public static class GoldenFixtures
{
    private const string RepositoryMarker = "MapGen.slnx";

    /// <summary>
    /// Resolves the fixtures root, starting the marker search at <paramref name="searchFrom"/>
    /// (a host's content root, or <c>AppContext.BaseDirectory</c> for a test assembly).
    /// </summary>
    public static string ResolveRoot(string? configuredRoot, string searchFrom)
    {
        if (!string.IsNullOrWhiteSpace(configuredRoot))
        {
            return configuredRoot;
        }

        var directory = new DirectoryInfo(searchFrom);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, RepositoryMarker)))
        {
            directory = directory.Parent;
        }

        string repositoryRoot = directory?.FullName ?? searchFrom;
        return Path.Combine(repositoryRoot, "tests", "fixtures", "golden");
    }
}
