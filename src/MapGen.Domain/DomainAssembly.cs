namespace MapGen.Domain;

/// <summary>
/// Assembly anchor for architecture tests and DI scanning.
/// The domain layer holds value objects, aggregates, domain services, and invariants.
/// It must stay free of framework, filesystem, clock, and serialization dependencies —
/// enforced by MapGen.ArchitectureTests.
/// </summary>
public static class DomainAssembly
{
}
