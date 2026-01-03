<?php
declare(strict_types=1);

namespace MapGenerator\TreePlanter\Engine;

use MapGenerator\TreePlanter\Job\JobLocator;
use MapGenerator\TreePlanter\Random\DeterministicRandomGenerator;
use MapGenerator\TreePlanter\Vegetation\VegetationSuitabilityCalculator;
use MapGenerator\TreePlanter\Vegetation\TreeTypeSelector;
use MapGenerator\TreePlanter\Debug\TreePlanterHtmlDebugWriter;

final class TreePlacementEngine
{
    /**
     * Execute exactly one TreePlanter job if available.
     *
     * @return int
     *   0 = success
     *   3 = no work available
     */
    public static function runOnce(string $rootDirectory): int
    {
        $jobLocator = new JobLocator(
            $rootDirectory . '/inbox/from_heightmap',
            $rootDirectory . '/inbox/from_tiler',
            $rootDirectory . '/inbox/from_weather'
        );

        $job = $jobLocator->findNextJob();

        // No work is a valid outcome for a queue worker
        if ($job === null) {
            return 3;
        }

        // ------------------------------------------------------------
        // Validate expected job shape
        // ------------------------------------------------------------

        foreach (['job_id', 'tiles', 'map_width_in_cells', 'map_height_in_cells'] as $key) {
            if (!array_key_exists($key, $job)) {
                throw new \RuntimeException(
                    "TreePlanter job missing required key: {$key}"
                );
            }
        }

        $jobIdentifier = $job['job_id'];
        $tiles = $job['tiles'];
        $mapWidthInCells = (int)$job['map_width_in_cells'];
        $mapHeightInCells = (int)$job['map_height_in_cells'];

        // ------------------------------------------------------------
        // Tree placement
        // ------------------------------------------------------------

        $random = new DeterministicRandomGenerator();
        $suitability = new VegetationSuitabilityCalculator();
        $selector = new TreeTypeSelector();

        foreach ($tiles as &$tile) {
            if (!$suitability->canPlaceTree($tile)) {
                continue;
            }

            if ($random->chance(0.35)) {
                $tile['decorations']['tree'] =
                    $selector->selectTreeType($tile);
            }
        }
        unset($tile);

        // ------------------------------------------------------------
        // Write world payload
        // ------------------------------------------------------------

        $jobLocator->writeWorldPayload(
            $jobIdentifier,
            $tiles,
            $mapWidthInCells,
            $mapHeightInCells
        );

        // ------------------------------------------------------------
        // Optional debug HTML
        // ------------------------------------------------------------

        if (getenv('TREEPLANTER_DEBUG_HTML') === '1') {
            (new TreePlanterHtmlDebugWriter())->write(
                $rootDirectory . '/debug',
                $jobIdentifier,
                $tiles,
                $mapWidthInCells,
                $mapHeightInCells
            );
        }

        return 0;
    }
}
