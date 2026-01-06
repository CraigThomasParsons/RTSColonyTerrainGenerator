<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Command;

use Minicli\Command\Command;
use Throwable;
use MapGenerator\TreePlanter\Job\JobLocator;
use MapGenerator\TreePlanter\Random\DeterministicRandomGenerator;
use MapGenerator\TreePlanter\Vegetation\VegetationSuitabilityCalculator;
use MapGenerator\TreePlanter\Vegetation\TreeTypeSelector;
use MapGenerator\TreePlanter\Vegetation\TreePlacementEngine;
use Minicli\Command\CommandController;

final class RunCommand extends CommandController
{
    public function handle(): void
    {
        $this->info("TreePlanter worker started");
        $this->loadEnvironment();
        $this->ensureInboxDirectories();

        $jobLocator = new JobLocator(
            $this->getHeightmapInbox(),
            $this->getMaptilesInbox(),
            $this->getWeatherInbox()
        );

        $job = $jobLocator->findNextJob();

        if ($job === null) {
            // Expected idle behavior
            return;
        }

        $this->info("Processing job {$job->getJobIdentifier()}");

        // Extract job data
        $tiles = $job->getTiles();
        $mapWidth = $job->getMapWidthInCells();
        $mapHeight = $job->getMapHeightInCells();
        $worldSeed = $job->getWorldSeed();

        // Core vegetation engine
        $engine = new TreePlacementEngine();

        $tiles = $engine->applyTrees(
            $tiles,
            $mapWidth,
            $mapHeight,
            $worldSeed,
            new VegetationSuitabilityCalculator(),
            new TreeTypeSelector(),
            new DeterministicRandomGenerator()
        );

        // Optional debug HTML
        if (getenv('TREEPLANTER_DEBUG_HTML') === '1') {
            $this->writeDebugHtml(
                $job->getJobIdentifier(),
                $tiles,
                $mapWidth,
                $mapHeight
            );
        }

        // Emit world payload
        $job->writeWorldPayload($tiles);

        $this->info("TreePlanter worker finished, Job Completed.");
    }

    // ------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------

    private function loadEnvironment(): void
    {
        $envPath = realpath(__DIR__ . '/../../../.env');

        if ($envPath === false) {
            return;
        }

        foreach (file($envPath, FILE_IGNORE_NEW_LINES) as $line) {
            if (str_starts_with(trim($line), '#') || !str_contains($line, '=')) {
                continue;
            }

            [$key, $value] = explode('=', $line, 2);
            putenv(trim($key) . '=' . trim($value));
        }
    }

    private function ensureInboxDirectories(): void
    {
        foreach ([
            $this->getHeightmapInbox(),
            $this->getMaptilesInbox(),
            $this->getWeatherInbox(),
        ] as $dir) {
            if (!is_dir($dir)) {
                mkdir($dir, 0777, true);
            }
        }
    }

    private function getHeightmapInbox(): string
    {
        return realpath(__DIR__ . '/../../inbox/from_heightmap')
            ?: __DIR__ . '/../../inbox/from_heightmap';
    }

    private function getMaptilesInbox(): string
    {
        return realpath(__DIR__ . '/../../inbox/from_tiler')
            ?: __DIR__ . '/../../inbox/from_tiler';
    }

    private function getWeatherInbox(): string
    {
        return realpath(__DIR__ . '/../../inbox/from_weather')
            ?: __DIR__ . '/../../inbox/from_weather';
    }

    private function writeDebugHtml(
        string $jobId,
        array $tiles,
        int $width,
        int $height
    ): void {
        try {
            $writer = new TreePlanterHtmlDebugWriter();

            $writer->write(
                __DIR__ . '/../../debug',
                $jobId,
                $tiles,
                $width,
                $height
            );

            $this->info("Debug HTML written: debug/{$jobId}.html");
        } catch (Throwable $e) {
            // Debug must never break pipeline
            $this->warning("Debug HTML failed: {$e->getMessage()}");
        }
    }
}
