using System.Security.Cryptography;
using System.Text.Json;

namespace MapGen.CompatibilityTests;

/// <summary>
/// Access to the Phase 0 golden-job fixtures under tests/fixtures/golden/.
///
/// Each job directory holds the small canonical artifacts (input.job.json, .heightmap,
/// .weather, .maptiles, .playable.json) plus a manifest.json of logical hashes for every
/// artifact the job produced — including the large ones (worldpayload, png, chk) that are
/// hashed but not stored.
///
/// The logical hash must agree with tools/artifact_hash (Python). For binary artifacts the
/// contract is simple: "sha256:" + lowercase hex of the raw bytes. Both sides implement
/// exactly that, which is what makes cross-language parity checks trustworthy.
/// </summary>
public static class GoldenFixtures
{
    public static readonly string[] JobIds =
    {
        "43860dcf-6469-42a7-9843-4e33abeacfac",
        "3c96b74c-6f86-4d27-a0ca-c567f385ae8e",
        "0860a05a-a410-4cc2-987d-a48a4cd120c7",
    };

    public static string RepoRoot { get; } = FindRepoRoot();

    public static string JobDir(string jobId) => Path.Combine(RepoRoot, "tests", "fixtures", "golden", jobId);

    public static string ArtifactPath(string jobId, string suffix)
        => Path.Combine(JobDir(jobId), $"{jobId}{suffix}");

    /// <summary>The recorded logical hash for a manifest entry, e.g. "MapGenerator/Tiler/outbox/&lt;job&gt;.maptiles".</summary>
    public static string ManifestHash(string jobId, string relPath)
    {
        var manifest = Path.Combine(JobDir(jobId), "manifest.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(manifest));
        var entry = doc.RootElement.GetProperty("artifacts").GetProperty(relPath);
        return entry.GetProperty("logical_sha256").GetString()!;
    }

    /// <summary>Logical hash of a binary artifact: "sha256:" + hex(sha256(bytes)). Mirrors tools/artifact_hash.</summary>
    public static string BinaryLogicalHash(string path)
    {
        var hex = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));
        return "sha256:" + hex;
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "MapGen.slnx")))
        {
            dir = dir.Parent;
        }
        if (dir is null)
        {
            throw new InvalidOperationException("Could not locate repository root (no MapGen.slnx found above the test assembly).");
        }
        return dir.FullName;
    }
}
