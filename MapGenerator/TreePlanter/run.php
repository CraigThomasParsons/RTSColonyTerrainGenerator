<?php

declare(strict_types=1);

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

$jobLocator =
    new JobLocator(
        $heightmapInboxDirectory,
        $maptilesInboxDirectory,
        $weatherInboxDirectory
    );

$randomGenerator = new DeterministicRandomGenerator();
$suitabilityCalculator = new VegetationSuitabilityCalculator();
$treeTypeSelector = new TreeTypeSelector();
