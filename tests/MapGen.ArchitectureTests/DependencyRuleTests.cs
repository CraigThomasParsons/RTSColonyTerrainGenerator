using MapGen.Application;
using MapGen.Contracts;
using MapGen.Domain;
using Mediator;
using NetArchTest.Rules;
using Xunit;

namespace MapGen.ArchitectureTests;

/// <summary>
/// Gate 5 of the CI quality gates (mapgen-spec-driven-planning/07-ci-quality-gates.md):
/// dependency direction is enforced by tests, not convention.
/// Every rule here names its enforcement path — this file IS the enforcement path.
/// </summary>
public class DependencyRuleTests
{
    [Fact]
    public void Domain_references_no_other_solution_layer()
    {
        var result = Types.InAssembly(typeof(DomainAssembly).Assembly)
            .Should()
            .NotHaveDependencyOnAny("MapGen.Application", "MapGen.Contracts", "MapGen.Infrastructure")
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    [Fact]
    public void Domain_does_not_touch_serialization_frameworks()
    {
        var result = Types.InAssembly(typeof(DomainAssembly).Assembly)
            .Should()
            .NotHaveDependencyOnAny("System.Text.Json", "Newtonsoft.Json", "System.Xml.Serialization")
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    [Fact]
    public void Domain_does_not_touch_the_filesystem()
    {
        // Deterministic domain rules must be free of clocks, random globals, and IO.
        // Artifact reading and writing belongs to infrastructure adapters.
        var result = Types.InAssembly(typeof(DomainAssembly).Assembly)
            .Should()
            .NotHaveDependencyOnAny("System.IO.File", "System.IO.Directory", "System.IO.FileStream")
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    [Fact]
    public void Contracts_is_a_leaf_assembly()
    {
        var result = Types.InAssembly(typeof(ContractsAssembly).Assembly)
            .Should()
            .NotHaveDependencyOnAny("MapGen.Domain", "MapGen.Application", "MapGen.Infrastructure")
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    [Fact]
    public void Application_does_not_reference_infrastructure()
    {
        var result = Types.InAssembly(typeof(ApplicationAssembly).Assembly)
            .Should()
            .NotHaveDependencyOn("MapGen.Infrastructure")
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    [Fact]
    public void Request_handlers_implement_the_mediator_handler_interface()
    {
        // ADR 0005: application request handlers are dispatched through Mediator, so every
        // type named *Handler must implement IRequestHandler<,> — no hand-called handlers.
        var result = Types.InAssembly(typeof(ApplicationAssembly).Assembly)
            .That()
            .HaveNameEndingWith("Handler")
            .Should()
            .ImplementInterface(typeof(IRequestHandler<,>))
            .GetResult();

        Assert.True(result.IsSuccessful, FailureList(result));
    }

    private static string FailureList(TestResult result)
        => result.IsSuccessful
            ? string.Empty
            : "Offending types: " + string.Join(", ", result.FailingTypeNames ?? new List<string>());
}
