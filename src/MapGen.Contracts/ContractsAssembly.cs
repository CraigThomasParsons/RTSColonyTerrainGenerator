namespace MapGen.Contracts;

/// <summary>
/// Assembly anchor for architecture tests.
/// Contracts carries only cross-context types: artifact schemas, stage manifests,
/// and the shapes other bounded contexts (or external consumers such as
/// AgileMedievalPeasantBoard's map-document payload) are allowed to see.
/// It is a leaf assembly: it references nothing in this solution.
/// </summary>
public static class ContractsAssembly
{
}
