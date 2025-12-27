using System;
using Tiler.IO;
using Tiler.Processing;

namespace Tiler
{
    /// <summary>
    /// Entry point for the Tiler batch processor.
    ///
    /// Currently this executable only validates that it can load a .heightmap file.
    /// Future stages will:
    /// - Compute terrain adjacency bitmasks per cell
    /// - Emit tile IDs into a .maptiles artifact
    /// - Optionally emit debug artifacts (HTML/mask dumps)
    /// </summary>
    internal static class Program
    {
        /// <summary>
        /// Main program entry.
        ///
        /// Usage:
        ///   dotnet run -- <path-to-heightmap>
        ///
        /// Returns:
        ///   0 on success
        ///   1 on argument error
        ///   2 on loading/parsing error
        /// </summary>
        private static int Main(string[] args)
        {
            if (args.Length != 1)
            {
                Console.Error.WriteLine("Usage: tiler <path-to-heightmap>");
                return 1;
            }

            string heightmapPath = args[0];
            var heightmap = HeightmapReader.Read(args[0]);
            var masks = CellBitmaskCalculator.ComputeMasks(heightmap);
            var tiles = TileIdResolver.Resolve(heightmap, masks);

            try
            {
                var data = HeightmapReader.Read(heightmapPath);

                Console.WriteLine("Loaded .heightmap successfully:");
                Console.WriteLine($"  Width (cells):  {data.WidthInCells}");
                Console.WriteLine($"  Height (cells): {data.HeightInCells}");
                Console.WriteLine($"  Seed:           {data.DeterministicSeed}");

                Console.WriteLine("Sample masks:");
                for (int y = 0; y < 5; y++)
                {
                    for (int x = 0; x < 5; x++)
                    {
                        Console.Write($"{masks[x, y],2} ");
                    }
                    Console.WriteLine();
                }

                Console.WriteLine("Sample tile IDs:");

                for (int y = 0; y < 6; y++)
                {
                    for (int x = 0; x < 6; x++)
                    {
                        Console.Write($"{tiles[x, y],4} ");
                    }
                    Console.WriteLine();
                }
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("Failed to load .heightmap:");
                Console.Error.WriteLine(ex.GetType().Name + ": " + ex.Message);
                return 2;
            }
        }
    }
}
