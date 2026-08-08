#!/usr/bin/env php
<?php

declare(strict_types=1);

/**
 * Capture a `.worldpayload` for each Golden Job by running the legacy TreePlanter stage
 * over the fixtures already committed under `tests/fixtures/golden/`.
 *
 * The Golden Jobs were captured without TreePlanter's own artifact, so the replayed
 * preview and map document had no canopy to project. TreePlanter needs only
 * `.heightmap`, `.maptiles` and `.weather` — all three are present in every fixture — so
 * the stage can be run without the legacy Tiler, which does not build.
 *
 * This tool composes the legacy stage's own classes exactly as `MapGenerator/TreePlanter/
 * run.php` does. It edits nothing under `MapGenerator/`: the legacy stage stays the
 * read-only baseline (AGENTS.md, "Repository Safety"), and the only new file is the
 * `<id>.worldpayload` written beside the fixtures it was derived from.
 *
 * Usage:
 *   php scripts/tools/capture_treeplanter_worldpayload.php [<golden-job-directory> ...]
 *
 * With no arguments every job directory under `tests/fixtures/golden/` is captured.
 */

const EXIT_CODE_SUCCESS = 0;
const EXIT_CODE_FAILURE = 1;

// Why: The stage's deterministic seed is fixed in run.php; capture must use the same one
// or the fixture would not match what the pipeline itself would have written.
const TREE_PLACEMENT_SEED = 12345;

$repositoryRoot = dirname(__DIR__, 2);

// Why: TreePlanter's committed `vendor/` is a stub — the Composer packages are not in the
// repository, so `vendor/autoload.php` cannot be loaded. The three stage classes this tool
// composes have no third-party dependency of their own, so they are required directly. That
// also keeps the capture runnable on a clean checkout, without a `composer install`.
require_once $repositoryRoot . '/MapGenerator/TreePlanter/src/Tile/TileAssembler.php';
require_once $repositoryRoot . '/MapGenerator/TreePlanter/src/Engine/TreePlacementEngine.php';
require_once $repositoryRoot . '/MapGenerator/TreePlanter/src/World/WorldPayloadWriter.php';

use MapGenerator\TreePlanter\Engine\TreePlacementEngine;
use MapGenerator\TreePlanter\Tile\TileAssembler;
use MapGenerator\TreePlanter\World\WorldPayloadWriter;

/**
 * Write a progress line to STDERR so STDOUT stays free for machine-readable output.
 */
function reportProgress(string $message): void
{
    fwrite(STDERR, '[capture-treeplanter] ' . $message . PHP_EOL);
}

/**
 * List the Golden Job directories to capture.
 *
 * @param array<int, string> $arguments Command-line arguments after the script name
 *
 * @return array<int, string> Absolute directory paths, in a stable order
 */
function resolveJobDirectories(array $arguments, string $repositoryRoot): array
{
    // Why: An explicit list lets a single fixture be re-captured in isolation.
    if (count($arguments) > 0) {
        return array_map(
            static function (string $argument): string {
                $resolved = realpath($argument);

                if ($resolved === false) {
                    throw new RuntimeException("Golden Job directory does not exist: {$argument}");
                }

                return $resolved;
            },
            $arguments
        );
    }

    $goldenRoot = $repositoryRoot . '/tests/fixtures/golden';
    $entries = glob($goldenRoot . '/*', GLOB_ONLYDIR);

    if ($entries === false) {
        throw new RuntimeException("Could not read the Golden Job root: {$goldenRoot}");
    }

    // Why: Ordinal order keeps the capture log comparable between runs.
    sort($entries, SORT_STRING);

    return $entries;
}

/**
 * Capture one Golden Job's `.worldpayload`.
 *
 * @return string Absolute path to the artifact written
 */
function captureJob(string $jobDirectory): string
{
    $jobSpecPath = $jobDirectory . '/input.job.json';

    if (!is_file($jobSpecPath)) {
        throw new RuntimeException("Golden Job spec not found: {$jobSpecPath}");
    }

    $jobSpecJson = file_get_contents($jobSpecPath);

    if ($jobSpecJson === false) {
        throw new RuntimeException("Could not read the Golden Job spec: {$jobSpecPath}");
    }

    $jobSpec = json_decode($jobSpecJson, true);

    if (!is_array($jobSpec)) {
        throw new RuntimeException("Golden Job spec is not a JSON object: {$jobSpecPath}");
    }

    $jobIdentifier = (string)$jobSpec['job_id'];
    $mapWidthInCells = (int)$jobSpec['map_width_in_cells'];
    $mapHeightInCells = (int)$jobSpec['map_height_in_cells'];

    $heightmapPath = $jobDirectory . '/' . $jobIdentifier . '.heightmap';
    $maptilesPath = $jobDirectory . '/' . $jobIdentifier . '.maptiles';
    $weatherPath = $jobDirectory . '/' . $jobIdentifier . '.weather';

    foreach ([$heightmapPath, $maptilesPath, $weatherPath] as $requiredArtifact) {
        // Why: The stage refuses an incomplete job; so must the capture.
        if (!is_file($requiredArtifact)) {
            throw new RuntimeException("Required Golden Job artifact is missing: {$requiredArtifact}");
        }
    }

    // Why: run.php infers dimensions from the heightmap's size rather than the job spec.
    // We keep the spec as the authority but cross-check the inference, so a fixture whose
    // spec disagrees with its bytes is reported instead of silently mis-assembled.
    $inferredWidthInCells = inferCellWidthFromHeightmap($heightmapPath);

    if ($inferredWidthInCells !== $mapWidthInCells) {
        throw new RuntimeException(
            "Heightmap implies {$inferredWidthInCells} cells across but the job spec "
            . "declares {$mapWidthInCells}: {$heightmapPath}"
        );
    }

    // Why: Tiler emits tiles at twice the cell resolution on each axis.
    $tileWidth = $mapWidthInCells * 2;
    $tileHeight = $mapHeightInCells * 2;

    $assembler = new TileAssembler();
    $tiles = $assembler->assemble($maptilesPath, $weatherPath, $tileWidth, $tileHeight);

    reportProgress("{$jobIdentifier}: assembled " . count($tiles) . ' tiles');

    $engine = new TreePlacementEngine(seed: TREE_PLACEMENT_SEED);
    $plantedTiles = $engine->run($tiles);

    $treeCount = countTrees($plantedTiles);
    reportProgress("{$jobIdentifier}: placed {$treeCount} trees");

    $writer = new WorldPayloadWriter();

    return $writer->write(
        $jobDirectory,
        $jobIdentifier,
        $mapWidthInCells,
        $mapHeightInCells,
        $plantedTiles
    );
}

/**
 * Infer the cell width the way `run.php` does: the heightmap body is two bytes per cell
 * and MapGenerator assumes square maps.
 */
function inferCellWidthFromHeightmap(string $heightmapPath): int
{
    $sizeInBytes = filesize($heightmapPath);

    if ($sizeInBytes === false) {
        throw new RuntimeException("Could not size the heightmap: {$heightmapPath}");
    }

    return (int)sqrt($sizeInBytes / 2);
}

/**
 * Count the tree decorations across an assembled tile list.
 *
 * @param array<int, array<string, mixed>> $tiles
 */
function countTrees(array $tiles): int
{
    $treeCount = 0;

    foreach ($tiles as $tile) {
        if (!isset($tile['decorations']) || !is_array($tile['decorations'])) {
            continue;
        }

        foreach ($tile['decorations'] as $decoration) {
            if (!is_array($decoration)) {
                continue;
            }

            if (($decoration['type'] ?? null) === 'tree') {
                $treeCount++;
            }
        }
    }

    return $treeCount;
}

// ------------------------------------------------------------
// Entry point
// ------------------------------------------------------------

try {
    $jobDirectories = resolveJobDirectories(array_slice($argv, 1), $repositoryRoot);

    if (count($jobDirectories) === 0) {
        reportProgress('No Golden Job directories found.');
        exit(EXIT_CODE_FAILURE);
    }

    foreach ($jobDirectories as $jobDirectory) {
        $writtenPath = captureJob($jobDirectory);
        reportProgress('wrote ' . $writtenPath);
        echo $writtenPath . PHP_EOL;
    }

    exit(EXIT_CODE_SUCCESS);
} catch (Throwable $exception) {
    reportProgress('capture failed: ' . $exception->getMessage());
    exit(EXIT_CODE_FAILURE);
}
