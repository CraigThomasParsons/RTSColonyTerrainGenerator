<?php
declare(strict_types=1);

/**
 * Load global MapGenerator environment variables.
 *
 * The .env file lives at:
 *   MapGenerator/.env
 *
 * TreePlanter is located at:
 *   MapGenerator/TreePlanter
 *
 * Therefore we traverse two levels up.
 */
$envFilePath =
    realpath(__DIR__ . '/../../.env');

/**
 * TreePlanter worker.
 *
 * This process joins heightmap, maptiles, and weather artifacts
 * for a single job identifier, places natural vegetation (trees only),
 * and emits a packaged world payload.
 *
 * Constraints:
 * - Deterministic output
 * - Stateless execution
 * - No man-made features
 * - No terrain mutation
 * - One job per invocation
 */

date_default_timezone_set('UTC');

const EXIT_CODE_SUCCESS = 0;
const EXIT_CODE_NO_WORK = 3;

require_once __DIR__ . '/vendor/autoload.php';

use MapGenerator\TreePlanter\Job\JobLocator;
use MapGenerator\TreePlanter\Random\DeterministicRandomGenerator;
use MapGenerator\TreePlanter\Vegetation\VegetationSuitabilityCalculator;
use MapGenerator\TreePlanter\Vegetation\TreeTypeSelector;

/**
 * Write a TreePlanter informational log message.
 *
 * This intentionally uses STDERR so systemd captures it.
 */
function logInfo(string $message): void
{
    fwrite(STDERR, "[TreePlanter] " . $message . PHP_EOL);
}

// ------------------------------------------------------------
// TreePlanter inbox directories
// ------------------------------------------------------------

// Resolve paths relative to TreePlanter root
$treePlanterRootDirectory = __DIR__;

$heightmapInboxDirectory =
    $treePlanterRootDirectory . '/inbox/from_heightmap';

$maptilesInboxDirectory =
    $treePlanterRootDirectory . '/inbox/from_tiler';

$weatherInboxDirectory =
    $treePlanterRootDirectory . '/inbox/from_weather';

foreach ([
    $heightmapInboxDirectory,
    $maptilesInboxDirectory,
    $weatherInboxDirectory,
] as $directory) {
    if (!is_dir($directory)) {
        mkdir($directory, 0777, true);
    }
}

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

            // Remove surrounding quotes if present
            if (
                strlen($value) >= 2 &&
                (
                    ($value[0] === '"' && $value[-1] === '"') ||
                    ($value[0] === "'" && $value[-1] === "'")
                )
            ) {
                $value = substr($value, 1, -1);
            }

            putenv($key . '=' . $value);
            $_ENV[$key] = $value;
        }
    }
}
$jobLocator =
    new JobLocator(
        $heightmapInboxDirectory,
        $maptilesInboxDirectory,
        $weatherInboxDirectory
    );

$job = $jobLocator->findNextJob();

// ------------------------------------------------------------
// No-op if no complete job is available
// ------------------------------------------------------------
// 1. Locate job
if ($job === null) {
    // TreePlanter is a queue worker.
    // Exiting cleanly when no work is available is expected behavior.
    exit(0);
}

// 2. Extract job data.
$jobIdentifier = $job->getJobIdentifier();
$tiles = $job->getTiles();
$mapWidthInCells = $job->getMapWidthInCells();
$mapHeightInCells = $job->getMapHeightInCells();

// 3. Process trees
$randomGenerator = new DeterministicRandomGenerator();
$suitabilityCalculator = new VegetationSuitabilityCalculator();
$treeTypeSelector = new TreeTypeSelector();

$engine = new TreePlacementEngine();

$tiles = $engine->applyTrees(
    $tiles,
    $job,
    $randomGenerator,
    $suitabilityCalculator,
    $treeTypeSelector
);

/**
 * Optional HTML debug output.
 *
 * This mirrors Tiler behavior exactly:
 * - gated by TREEPLANTER_DEBUG_HTML
 * - written to TreePlanter/debug/<job-id>.html
 * - never required for correctness
 */
$treePlanterDebugHtml =
    getenv('TREEPLANTER_DEBUG_HTML');

if ($treePlanterDebugHtml === '1') {
    try {
        $debugWriter = new TreePlanterHtmlDebugWriter();

        $debugWriter->write(
            $treePlanterRootDirectory . '/debug',
            $jobIdentifier,
            $tiles,
            $mapWidthInCells,
            $mapHeightInCells
        );

        logInfo(
            'Wrote TreePlanter debug HTML: debug/' .
            $jobIdentifier . '.html'
        );
    } catch (Throwable $exception) {
        // Debug output must never break the pipeline
        logInfo(
            'TreePlanter debug HTML generation failed: ' .
            $exception->getMessage()
        );
    }
}
