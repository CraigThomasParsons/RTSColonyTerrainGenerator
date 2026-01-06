using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Tiler.IO;
using Tiler.Processing;
using Tiler.Util;
using Tiler.Logging;

namespace Tiler
{
    internal static class Program
    {
        private enum ExitCode
        {
            Success = 0,
            InvalidArguments = 1,
            InputError = 2,
            OutputError = 3,
            UnexpectedError = 9
        }

        private static int Main(string[] args)
        {
            // ------------------------------------------------------------
            // Environment & culture setup
            // ------------------------------------------------------------

            DotEnv.Load(Path.GetFullPath(
                Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "..",
                    "..",
                    ".env"
                )
            ));

            CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
            CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;

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
            string jobId = Path.GetFileNameWithoutExtension(inputHeightmapPath);

            bool debugSamples = false;

            for (int i = 1; i < args.Length; i++)
            {
                if (args[i] == "--debug-samples")
                {
                    debugSamples = true;
                }
                else
                {
                    Console.Error.WriteLine($"Unknown argument: {args[i]}");
                    PrintUsage();
                    return (int)ExitCode.InvalidArguments;
                }
            }

            var logger = new MapGenStageLogger(jobId, "tiler");

            try
            {
                logger.Info(
                    "stage_started",
                    "Tiler stage started",
                    new Dictionary<string, string>
                    {
                        { "pid", Environment.ProcessId.ToString() },
                        { "input_path", inputHeightmapPath }
                    }
                );

                // ------------------------------------------------------------
                // Input validation
                // ------------------------------------------------------------

                if (!File.Exists(inputHeightmapPath))
                {
                    logger.Error(
                        "input_missing",
                        "Input heightmap file does not exist",
                        new Dictionary<string, string>
                        {
                            { "path", inputHeightmapPath }
                        }
                    );

                    return (int)ExitCode.InputError;
                }

                Directory.CreateDirectory("outbox");
                Directory.CreateDirectory("debug");

                // ------------------------------------------------------------
                // Load heightmap
                // ------------------------------------------------------------

                logger.Info("load_heightmap_begin", "Loading heightmap");

                var heightmap = HeightmapReader.Read(inputHeightmapPath);

                logger.Info(
                    "load_heightmap_success",
                    "Heightmap loaded",
                    new Dictionary<string, string>
                    {
                        { "width", heightmap.WidthInCells.ToString() },
                        { "height", heightmap.HeightInCells.ToString() },
                        { "seed", heightmap.DeterministicSeed.ToString() }
                    }
                );

                // ------------------------------------------------------------
                // Core tiler pipeline
                // ------------------------------------------------------------

                logger.Info("compute_masks_begin", "Computing adjacency bitmasks");
                var cellMasks = CellBitmaskCalculator.ComputeMasks(heightmap);

                logger.Info("resolve_tiles_begin", "Resolving tile IDs");
                var tileIds = TileIdResolver.Resolve(heightmap, cellMasks);

                // ------------------------------------------------------------
                // Write .maptiles
                // ------------------------------------------------------------

                string outputPath = Path.Combine(
                    "outbox",
                    jobId + ".maptiles"
                );

                logger.Info(
                    "write_maptiles_begin",
                    "Writing .maptiles output",
                    new Dictionary<string, string>
                    {
                        { "output_path", outputPath }
                    }
                );

                MapTilesWriter.Write(
                    outputPath,
                    tileIds,
                    heightmap.DeterministicSeed
                );

                logger.Info(
                    "write_maptiles_success",
                    ".maptiles written successfully",
                    new Dictionary<string, string>
                    {
                        { "tile_width", tileIds.GetLength(0).ToString() },
                        { "tile_height", tileIds.GetLength(1).ToString() }
                    }
                );

                // ------------------------------------------------------------
                // Optional HTML debug export
                // ------------------------------------------------------------

                if (debugHtml)
                {
                    string htmlPath = Path.Combine(
                        "debug",
                        jobId + ".html"
                    );

                    logger.Info(
                        "debug_html_begin",
                        "Writing HTML debug output",
                        new Dictionary<string, string>
                        {
                            { "path", htmlPath }
                        }
                    );

                    HtmlTileDebugWriter.Write(htmlPath, tileIds);
                }

                logger.Info("stage_finished", "Tiler stage completed successfully");

                return (int)ExitCode.Success;
            }
            catch (InvalidDataException ex)
            {
                logger.Error(
                    "input_invalid",
                    "Invalid heightmap data",
                    new Dictionary<string, string>
                    {
                        { "error", ex.Message }
                    }
                );

                Console.Error.WriteLine(ex.Message);
                return (int)ExitCode.InputError;
            }
            catch (IOException ex)
            {
                logger.Error(
                    "io_error",
                    "I/O error during tiler execution",
                    new Dictionary<string, string>
                    {
                        { "error", ex.Message }
                    }
                );

                Console.Error.WriteLine(ex.Message);
                return (int)ExitCode.OutputError;
            }
            catch (Exception ex)
            {
                logger.Error(
                    "unexpected_error",
                    "Unexpected tiler failure",
                    new Dictionary<string, string>
                    {
                        { "exception", ex.ToString() }
                    }
                );

                Console.Error.WriteLine(ex);
                return (int)ExitCode.UnexpectedError;
            }
        }

        private static void PrintUsage()
        {
            Console.Error.WriteLine("Usage:");
            Console.Error.WriteLine("  tiler <path-to-heightmap> [--debug-samples]");
        }
    }
}
