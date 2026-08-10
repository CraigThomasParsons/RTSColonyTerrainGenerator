using System.Text.Json;
using MapGen.Application;
using MapGen.Application.TileResolution;
using Mediator;
using Microsoft.Extensions.DependencyInjection;

namespace MapGen.Cli;

/// <summary>
/// Minimal command-line seam over the application layer — the `net` target the BDD lane
/// drives (cucumber-js -p net). One subcommand per CQRS operation; JSON out; failures
/// print {"error":"..."} and exit 1. Every command dispatches through Mediator (ADR 0005).
///
///   MapGen.Cli expand-cell --width 10 --height 10 --x 3 --y 4
///   MapGen.Cli mask-cell   --width 3 --height 3 --x 1 --y 1 --terrain 1,1,1,1,1,1,1,1,1
/// </summary>
public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        if (args.Length == 0)
        {
            return Fail("Usage: MapGen.Cli <expand-cell|mask-cell> [options]");
        }

        await using var provider = new ServiceCollection()
            .AddMapGenApplication()
            .BuildServiceProvider();
        var sender = provider.GetRequiredService<ISender>();

        return args[0] switch
        {
            "expand-cell" => await ExpandCell(sender, ParseOptions(args)),
            "mask-cell" => await MaskCell(sender, ParseOptions(args)),
            _ => Fail($"Unknown command '{args[0]}'. Expected expand-cell or mask-cell."),
        };
    }

    private static async Task<int> ExpandCell(ISender sender, Options options)
    {
        if (!options.Require("width", "height", "x", "y", out string? missing))
        {
            return Fail($"Missing required option --{missing}.");
        }

        var result = await sender.Send(new ResolveTileRegionCommand(
            CellX: options["x"], CellY: options["y"],
            MapWidthInCells: options["width"], MapHeightInCells: options["height"]));

        if (!result.IsSuccess)
        {
            return Fail(result.Error!);
        }

        return Print(new
        {
            cell = new { x = options["x"], y = options["y"] },
            tiles = result.Value!.Coordinates.Select(t => new { x = t.X, y = t.Y }).ToArray(),
        });
    }

    private static async Task<int> MaskCell(ISender sender, Options options)
    {
        if (!options.Require("width", "height", "x", "y", out string? missing))
        {
            return Fail($"Missing required option --{missing}.");
        }

        if (options.Terrain is null)
        {
            return Fail("Missing required option --terrain (row-major comma-separated grid).");
        }

        var result = await sender.Send(new ComputeAdjacencyMaskCommand(
            CellX: options["x"], CellY: options["y"],
            GridWidth: options["width"], GridHeight: options["height"],
            Terrain: options.Terrain));

        if (!result.IsSuccess)
        {
            return Fail(result.Error!);
        }

        var mask = result.Value!;
        return Print(new
        {
            cell = new { x = options["x"], y = options["y"] },
            mask = (int)mask.Value,
            north = mask.HasNorth,
            east = mask.HasEast,
            south = mask.HasSouth,
            west = mask.HasWest,
        });
    }

    private sealed class Options
    {
        private readonly Dictionary<string, int> _ints = new();
        public IReadOnlyList<int>? Terrain { get; set; }

        public int this[string key] => _ints[key];
        public void SetInt(string key, int value) => _ints[key] = value;

        public bool Require(string a, string b, string c, string d, out string? missing)
        {
            foreach (string key in new[] { a, b, c, d })
            {
                if (!_ints.ContainsKey(key))
                {
                    missing = key;
                    return false;
                }
            }
            missing = null;
            return true;
        }
    }

    private static Options ParseOptions(string[] args)
    {
        var options = new Options();
        for (int i = 1; i + 1 < args.Length; i += 2)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }
            string key = args[i][2..];
            if (key == "terrain")
            {
                options.Terrain = args[i + 1].Split(',', StringSplitOptions.RemoveEmptyEntries)
                    .Select(int.Parse).ToArray();
            }
            else if (int.TryParse(args[i + 1], out int value))
            {
                options.SetInt(key, value);
            }
        }
        return options;
    }

    private static int Print(object payload)
    {
        Console.WriteLine(JsonSerializer.Serialize(payload));
        return 0;
    }

    private static int Fail(string message)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { error = message }));
        return 1;
    }
}
