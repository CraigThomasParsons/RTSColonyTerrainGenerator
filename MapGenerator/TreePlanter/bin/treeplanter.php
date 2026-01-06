#!/usr/bin/env php
<?php

declare(strict_types=1);

require __DIR__ . '/../vendor/autoload.php';

if(php_sapi_name() !== 'cli') {
    exit;
}

use MapGenerator\TreePlanter\Engine\TreePlacementEngine;

use Minicli\App;

$app = new App([
    'app_path' => [
        __DIR__ . '/app/Command',
    ],
    'theme' => '\Unicorn', 
    'debug' => false,
]);


$app->registerCommand('run', function () use ($app) {
    $rootDirectory = realpath(__DIR__ . '/..');

    $exitCode = TreePlacementEngine::runOnce($rootDirectory);

    if ($exitCode === 3) {
        $app->info('No TreePlanter jobs available.');
        exit(3);
    }

    if ($exitCode === 0) {
        $app->success('TreePlanter job completed.');
        exit(0);
    }

    $app->error('TreePlanter failed unexpectedly.');
    exit(1);
});

$app->registerCommand('assemble', function () use ($app) {
    $assembler = new \RTSColonyTerrainGenerator\TreePlanter\Tile\TileAssembler();

    // Hardcode ONE known job for now
    $tiles = $assembler->assemble(
        __DIR__ . '/../debug/test.maptiles',
        __DIR__ . '/../debug/test.weather',
        16,
        16
    );

    $app->info('Assembled tiles: ' . count($tiles));
    $app->info(json_encode($tiles[0], JSON_PRETTY_PRINT));

    exit(0);
});


$app->registerCommand('write-test', function () use ($app) {
    $writer = new \MapGenerator\TreePlanter\World\WorldPayloadWriter();

    $tiles = [
        [
            'x' => 0,
            'y' => 0,
            'terrain' => 'grass',
            'weather' => null,
            'decorations' => [],
        ],
    ];

    $path = $writer->write(
        __DIR__ . '/../debug',
        'test-job',
        1,
        1,
        $tiles
    );

    $app->success("Wrote world payload: {$path}");
});

//  This is a very basic test command for development purposes only.
$app->registerCommand('place-test', function () use ($app) {
    $tiles = [
        [
            'x' => 0,
            'y' => 0,
            'terrain' => 'grass',
            'weather' => null,
            'decorations' => [],
        ],
        [
            'x' => 1,
            'y' => 0,
            'terrain' => 'taiga',
            'weather' => null,
            'decorations' => [],
        ],
        [
            'x' => 2,
            'y' => 0,
            'terrain' => 'rock',
            'weather' => null,
            'decorations' => [],
        ],
    ];

    $mutated = \MapGenerator\TreePlanter\Engine\TreePlacementEngine::placeTrees($tiles);

    $app->info(json_encode($mutated, JSON_PRETTY_PRINT));
    exit(0);
});

/**
 * This tells MiniCLI:
 * - Look for commands in src/Command
 * - Match CLI command names automatically
 */
$app->runCommand($argv);

$engine = new TreePlacementEngine(
    seed: $job->seed ?? 12345
);

$treePlacements = $engine->run($tileAssembler);

$worldPayloadWriter->write(
    tiles: $tileAssembler,
    treePlacements: $treePlacements
);
