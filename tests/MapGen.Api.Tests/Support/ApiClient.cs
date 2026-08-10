using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace MapGen.Api.Tests.Support;

/// <summary>
/// Thin request helpers. Tests assert against the raw JSON — the wire is the contract, and
/// a C# DTO round-trip would hide a renamed field, which is precisely the failure the
/// hand-written TypeScript mirror needs guarding against.
/// </summary>
public static class ApiClient
{
    public static Task<HttpResponseMessage> PostJson(this HttpClient client, string path, string json)
        => client.PostAsync(path, new StringContent(json, Encoding.UTF8, "application/json"));

    public static async Task<JsonElement> ReadJson(this HttpResponseMessage response)
    {
        string body = await response.Content.ReadAsStringAsync();
        return JsonDocument.Parse(body).RootElement.Clone();
    }

    /// <summary>Submits a job and returns the accepted body, failing loudly on a non-202.</summary>
    public static async Task<JsonElement> SubmitWorld(this HttpClient client, long seed = 1234567890, string? name = "Default Forest")
    {
        var payload = new Dictionary<string, object?>
        {
            ["seed"] = seed,
            ["map_width_in_cells"] = 64,
            ["map_height_in_cells"] = 64,
            ["name"] = name,
        };

        var response = await client.PostAsJsonAsync("/api/v1/worlds", payload);
        Assert.Equal(System.Net.HttpStatusCode.Accepted, response.StatusCode);
        return await response.ReadJson();
    }

    public static string JobId(this JsonElement body) => body.GetProperty("job_id").GetString()!;

    public static IReadOnlyList<string> PropertyNames(this JsonElement element)
        => element.EnumerateObject().Select(property => property.Name).ToArray();
}
