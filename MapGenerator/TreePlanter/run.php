<?php
declare(strict_types=1);

/**
 * Load global MapGenerator environment variables.
 */
$envFilePath = realpath(__DIR__ . '/../../.env');

date_default_timezone_set('UTC');

const EXIT_CODE_SUCCESS = 0;
const EXIT_CODE_NO_WORK = 3;

require_once __DIR__ . '/vendor/autoload.php';

use MapGenerator\TreePlanter\Job\JobLocator;
use MapGenerator\TreePlanter\Logging\StageLogger;
use MapGenerator\TreePlanter\Tile\TileAssembler;
use MapGenerator\TreePlanter\Engine\TreePlacementEngine;
use MapGenerator\TreePlanter\World\WorldPayloadWriter;

/**
 * Write a TreePlanter informational log message to STDERR.
 */
function logInfo(string $message): void
{
    fwrite(STDERR, "[TreePlanter] " . $message . PHP_EOL);
}

// ------------------------------------------------------------
// Environment Setup
// ------------------------------------------------------------

if ($envFilePath !== false && is_file($envFilePath)) {
    $envLines = file($envFilePath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if (is_array($envLines)) {
        foreach ($envLines as $line) {
            if (str_starts_with(trim($line), '#')) {
                continue;
            }
            if (strpos($line, '=') === false) {
                continue;
            }
            [$key, $value] = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value);
            if (strlen($value) >= 2 && (($value[0] === '"' && $value[-1] === '"') || ($value[0] === "'" && $value[-1] === "'"))) {
                $value = substr($value, 1, -1);
            }
            putenv($key . '=' . $value);
            $_ENV[$key] = $value;
        }
    }
}

// ------------------------------------------------------------
// Job Location
// ------------------------------------------------------------

$treePlanterRootDirectory = __DIR__;

// Point directly to upstream outboxes to avoid fragile symlinks in inbox
// These paths are relative to: MapGenerator/TreePlanter/
$heightmapInboxDirectory = realpath($treePlanterRootDirectory . '/../Heightmap/outbox');
$maptilesInboxDirectory = realpath($treePlanterRootDirectory . '/../Tiler/outbox');
$weatherInboxDirectory = realpath($treePlanterRootDirectory . '/../WeatherAnalyses/outbox');

// Fallback if realpath fails (should not happen if pipeline ran, but robust check)
if ($heightmapInboxDirectory === false) {
    $heightmapInboxDirectory = $treePlanterRootDirectory . '/../Heightmap/outbox';
}
if ($maptilesInboxDirectory === false) {
    $maptilesInboxDirectory = $treePlanterRootDirectory . '/../Tiler/outbox';
}
if ($weatherInboxDirectory === false) {
    $weatherInboxDirectory = $treePlanterRootDirectory . '/../WeatherAnalyses/outbox';
}

$jobLocator = new JobLocator(
    $heightmapInboxDirectory,
    $maptilesInboxDirectory,
    $weatherInboxDirectory
);

$job = $jobLocator->findNextJob();

if ($job === null) {
    // No job found. 
    // This is expected if the upstream files are missing or incomplete.
    // We log to stderr for systemd but cannot create a JSON job log.
    logInfo('No complete job found in upstream outboxes.');
    exit(EXIT_CODE_SUCCESS); 
}

// Extract job ID from array
$jobIdentifier = $job['job_id'];

// Initialize Logger
$logger = new StageLogger($jobIdentifier);
$logger->info('stage_start', 'TreePlanter stage started');
$logger->info('job_detected', "Processing job: {$jobIdentifier}");
$logger->info('input_source', "Reading independently from upstream outboxes");

try {
    // ------------------------------------------------------------
    // 1. Calculate Dimensions
    // ------------------------------------------------------------
    // We infer dimensions from the raw heightmap binary size (2 bytes per cell)
    $heightmapPath = $job['heightmap'];
    $heightmapSizeBytes = filesize($heightmapPath);
    if ($heightmapSizeBytes === false) {
        throw new RuntimeException("Could not read filesize of heightmap: {$heightmapPath}");
    }
    $totalCells = $heightmapSizeBytes / 2;
    $mapWidthInCells = (int)sqrt($totalCells);
    $mapHeightInCells = $mapWidthInCells; // Assuming square map

    $logger->info('dimensions_calculated', "Map dimensions: {$mapWidthInCells}x{$mapHeightInCells}");

    // ------------------------------------------------------------
    // 2. Assemble Tiles
    // ------------------------------------------------------------
    $logger->info('assembly_start', "Assembling tiles from inputs");
    
    $tileAssembler = new TileAssembler();
    $tiles = $tileAssembler->assemble(
        $job['maptiles'],
        $job['weather'],
        $mapWidthInCells,
        $mapHeightInCells
    );

    $logger->info('tiles_assembled', "Assembled " . count($tiles) . " tiles");

    // ------------------------------------------------------------
    // 3. Place Trees
    // ------------------------------------------------------------
    $logger->info('engine_start', 'TreePlacementEngine starting');

    // Use job ID hash or similar for seed if needed, but fixed seed is fine for now
    $engine = new TreePlacementEngine(seed: 12345);
    $processedTiles = $engine->run($tiles);

    $logger->info('engine_complete', 'TreePlacementEngine finished');

    // ------------------------------------------------------------
    // 4. Write Output
    // ------------------------------------------------------------
    $logger->info('payload_write_start', 'Writing world payload');

    $writer = new WorldPayloadWriter();
    $outboxDirectory = $treePlanterRootDirectory . '/outbox';
    
    if (!is_dir($outboxDirectory)) {
        mkdir($outboxDirectory, 0755, true);
    }

    $outputPath = $writer->write(
        $outboxDirectory,
        $jobIdentifier,
        $mapWidthInCells,
        $mapHeightInCells,
        $processedTiles
    );

    $logger->info('payload_written', "World payload written to: {$outputPath}");

    // ------------------------------------------------------------
    // 5. Cleanup / Archive (Optional - not implemented in JobLocator yet)
    // ------------------------------------------------------------
    // Ideally we would move inputs to archive, but since they are symlinked upstream outboxes,
    // we should NOT touch them. The upstream stages manage archival.
    // We just finish.

    $logger->info('stage_complete', 'TreePlanter stage completed successfully');
    logInfo("Stage completed for job: {$jobIdentifier}");

    exit(EXIT_CODE_SUCCESS);

} catch (Throwable $e) {
    if (isset($logger)) {
        $logger->error('stage_failed', $e->getMessage());
    }
    logInfo("TreePlanter failed: " . $e->getMessage());
    exit(1);
}
