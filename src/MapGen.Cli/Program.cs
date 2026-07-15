using System.Text.Json;
using MapGen.Application.TileResolution;

namespace MapGen.Cli;

/// <summary>
/// Minimal command-line seam over the application layer — the `net` target the BDD
/// lane drives (cucumber-js -p net). One command per CQRS operation; JSON out.
///
///   MapGen.Cli expand-cell --width 10 --height 10 --x 3 --y 4
///     -> {"cell":{"x":3,"y":4},"tiles":[{"x":6,"y":8},{"x":7,"y":8},{"x":6,"y":9},{"x":7,"y":9}]}
///
/// Failures print {"error":"..."} and exit 1.
/// </summary>
public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0 || args[0] != "expand-cell")
        {
            return Fail("Usage: MapGen.Cli expand-cell --width <n> --height <n> --x <n> --y <n>");
        }

        var options = new Dictionary<string, int>();
        for (int i = 1; i + 1 < args.Length; i += 2)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal) || !int.TryParse(args[i + 1], out int value))
            {
                return Fail($"Malformed argument pair: '{args[i]} {args[i + 1]}'.");
            }
            options[args[i][2..]] = value;
        }

        foreach (string required in new[] { "width", "height", "x", "y" })
        {
            if (!options.ContainsKey(required))
            {
                return Fail($"Missing required option --{required}.");
            }
        }

        var handler = new ResolveTileRegionHandler();
        var result = handler.Handle(new ResolveTileRegionCommand(
            CellX: options["x"],
            CellY: options["y"],
            MapWidthInCells: options["width"],
            MapHeightInCells: options["height"]));

        if (!result.IsSuccess)
        {
            return Fail(result.Error!);
        }

        var region = result.Value!;
        var payload = new
        {
            cell = new { x = options["x"], y = options["y"] },
            tiles = region.Coordinates.Select(t => new { x = t.X, y = t.Y }).ToArray(),
        };
        Console.WriteLine(JsonSerializer.Serialize(payload));
        return 0;
    }

    private static int Fail(string message)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { error = message }));
        return 1;
    }
}
