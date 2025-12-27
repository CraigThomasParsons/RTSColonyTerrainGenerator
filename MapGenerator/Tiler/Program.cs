using System;
using System.Globalization;
using System.IO;
using Tiler.IO;
using Tiler.Processing;
using Tiler.Util;

namespace Tiler
{
    /// <summary>
    /// Entry point for the Tiler batch processor.
    ///
    /// Responsibilities:
    /// - Read an authoritative .heightmap file
    /// - Compute deterministic per-cell adjacency bitmasks (4-bit N/E/S/W)
    /// - Resolve final tile IDs and expand each cell to a 2×2 tile block
    /// - Emit a deterministic .maptiles artifact into the Tiler outbox
    /// - Optionally emit human-readable debug artifacts (HTML, console)
    /// - Archive the processed heightmap on success
    ///
    /// This executable is intentionally NOT creative:
    /// - No randomness
    /// - No terrain modifications
    /// - No procedural world logic
    /// </summary>
    internal static class Program
    {
        /// <summary>
        /// Process exit codes.
        /// These help systemd/Bash workers classify failures.
        /// </summary>
        private enum ExitCode
        {
            Success = 0,
            InvalidArguments = 1,
            InputError = 2,
            OutputError = 3,
            UnexpectedError = 9
        }

        /// <summary>
        /// Main program entrypoint.
        /// </summary>
        private static int Main(string[] args)
        {
            // ------------------------------------------------------------
            // Environment & culture setup
            // ------------------------------------------------------------

            // Load .env from repository root (working directory)
            DotEnv.Load(Path.GetFullPath(
                Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "..",
                    "..",
                    ".env"
                )
            ));

            // Force invariant culture to avoid locale-dependent output
            CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
            CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;

            // Read debug flags from environment
            bool debugHtml = DotEnv.GetBool("TILER_DEBUG_HTML");

            // ------------------------------------------------------------
            // Argument parsing
            // ------------------------------------------------------------

            if (args.Length < 1)
            {
                PrintUsage();
                return (int)ExitCode.InvalidArguments;
            }

            string inputHeightmapPath = args[0];

            // Defaults aligned to pipeline layout
            // All paths are relative to the Tiler working directory
            string outboxDir = "outbox";
            string archiveDir = "archive";
            string debugDir = "debug";


            bool debugSamples = false;

            for (int i = 1; i < args.Length; i++)
            {
                string arg = args[i];

                if (arg == "--debug-samples")
                {
                    debugSamples = true;
                }
                else
                {
                    Console.Error.WriteLine($"Unknown argument: {arg}");
                    PrintUsage();
                    return (int)ExitCode.InvalidArguments;
                }
            }

            try
            {
                // ------------------------------------------------------------
                // Input validation
                // ------------------------------------------------------------

                if (!File.Exists(inputHeightmapPath))
                {
                    Console.Error.WriteLine($"Input file not found: {inputHeightmapPath}");
                    return (int)ExitCode.InputError;
                }

                Directory.CreateDirectory(outboxDir);
                Directory.CreateDirectory(archiveDir);
                Directory.CreateDirectory(debugDir);

                // ------------------------------------------------------------
                // Load heightmap
                // ------------------------------------------------------------

                var heightmap = HeightmapReader.Read(inputHeightmapPath);

                Console.WriteLine("Loaded .heightmap successfully:");
                Console.WriteLine($"  Width (cells):  {heightmap.WidthInCells}");
                Console.WriteLine($"  Height (cells): {heightmap.HeightInCells}");
                Console.WriteLine($"  Seed:           {heightmap.DeterministicSeed}");

                // ------------------------------------------------------------
                // Core tiler pipeline
                // ------------------------------------------------------------

                var cellMasks = CellBitmaskCalculator.ComputeMasks(heightmap);
                var tileIds = TileIdResolver.Resolve(heightmap, cellMasks);

                // ------------------------------------------------------------
                // Write .maptiles
                // ------------------------------------------------------------

                string inputBaseName = Path.GetFileNameWithoutExtension(inputHeightmapPath);
                string outputFileName = inputBaseName + ".maptiles";
                string outputPath = Path.Combine(outboxDir, outputFileName);

                MapTilesWriter.Write(outputPath, tileIds, heightmap.DeterministicSeed);

                Console.WriteLine("Wrote .maptiles successfully:");
                Console.WriteLine($"  Output:    {outputPath}");
                Console.WriteLine($"  Tile size: {tileIds.GetLength(0)} × {tileIds.GetLength(1)}");

                // ------------------------------------------------------------
                // Optional console debug samples
                // ------------------------------------------------------------

                if (debugSamples)
                {
                    Console.WriteLine();
                    Console.WriteLine("Sample masks:");
                    PrintSampleByteGrid(cellMasks, 5, 5);

                    Console.WriteLine();
                    Console.WriteLine("Sample tile IDs:");
                    PrintSampleUShortGrid(tileIds, 6, 6);
                }

                // ------------------------------------------------------------
                // Optional HTML debug export (ENV-gated)
                // ------------------------------------------------------------

                if (debugHtml)
                {
                    string htmlPath = Path.Combine(
                        debugDir,
                        inputBaseName + ".html"
                    );

                    HtmlTileDebugWriter.Write(htmlPath, tileIds);

                    Console.WriteLine();
                    Console.WriteLine("Wrote HTML debug view:");
                    Console.WriteLine($"  Debug HTML: {htmlPath}");
                }

                // ------------------------------------------------------------
                // Archive input heightmap (final step)
                // ------------------------------------------------------------

                string archivedPath = Path.Combine(
                    archiveDir,
                    Path.GetFileName(inputHeightmapPath)
                );

                File.Move(inputHeightmapPath, archivedPath, overwrite: true);

                Console.WriteLine();
                Console.WriteLine("Archived input heightmap:");
                Console.WriteLine($"  {archivedPath}");

                return (int)ExitCode.Success;
            }
            catch (InvalidDataException ex)
            {
                Console.Error.WriteLine("Input error (invalid .heightmap):");
                Console.Error.WriteLine(ex.Message);
                return (int)ExitCode.InputError;
            }
            catch (IOException ex)
            {
                Console.Error.WriteLine("I/O error:");
                Console.Error.WriteLine(ex.Message);
                return (int)ExitCode.OutputError;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("Unexpected error:");
                Console.Error.WriteLine(ex);
                return (int)ExitCode.UnexpectedError;
            }
        }

        // ------------------------------------------------------------
        // Helpers
        // ------------------------------------------------------------

        private static void PrintUsage()
        {
            Console.Error.WriteLine("Usage:");
            Console.Error.WriteLine("  tiler <path-to-heightmap> [--debug-samples]");
        }

        private static void PrintSampleByteGrid(byte[,] grid, int sampleWidth, int sampleHeight)
        {
            int w = Math.Min(sampleWidth, grid.GetLength(0));
            int h = Math.Min(sampleHeight, grid.GetLength(1));

            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    Console.Write($"{grid[x, y],2} ");
                }
                Console.WriteLine();
            }
        }

        private static void PrintSampleUShortGrid(ushort[,] grid, int sampleWidth, int sampleHeight)
        {
            int w = Math.Min(sampleWidth, grid.GetLength(0));
            int h = Math.Min(sampleHeight, grid.GetLength(1));

            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    Console.Write($"{grid[x, y],4} ");
                }
                Console.WriteLine();
            }
        }
    }
}
