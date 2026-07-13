namespace MapGen.Application;

/// <summary>
/// Assembly anchor for architecture tests and DI scanning.
/// The application layer holds CQRS commands, queries, and their handlers.
/// Handlers orchestrate — validate input, load state, call the domain, persist,
/// record stage state — and must not reproduce domain arithmetic.
/// </summary>
public static class ApplicationAssembly
{
}
