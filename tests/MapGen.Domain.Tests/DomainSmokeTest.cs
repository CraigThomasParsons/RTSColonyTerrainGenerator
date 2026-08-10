using Xunit;

namespace MapGen.Domain.Tests;

/// <summary>
/// Placeholder until Epic 1 (verified cell-to-tile expansion) lands its value objects.
/// Epic 1 replaces this with example-based tests plus FsCheck property tests
/// (determinism, uniqueness, bounds) mirroring the Dafny contract.
/// </summary>
public class DomainSmokeTest
{
    [Fact]
    public void Domain_assembly_loads()
    {
        Assert.NotNull(typeof(DomainAssembly).Assembly);
    }
}
