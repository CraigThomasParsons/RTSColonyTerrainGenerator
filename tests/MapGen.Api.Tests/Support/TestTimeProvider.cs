namespace MapGen.Api.Tests.Support;

/// <summary>
/// A clock the test drives. Job progress is a pure function of the clock, so stepping this
/// forward walks a job through queued → running → succeeded with no sleeping and no
/// flakiness.
/// </summary>
public sealed class TestTimeProvider : TimeProvider
{
    private DateTimeOffset _utcNow;

    public TestTimeProvider(DateTimeOffset start) => _utcNow = start;

    public override DateTimeOffset GetUtcNow() => _utcNow;

    public void Advance(TimeSpan by) => _utcNow += by;
}
