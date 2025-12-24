<?php
/**
 * Front controller for Heightmap API
 *
 * Responsibilities:
 * - Bootstrap autoloader
 * - Route request to controller
 */

declare(strict_types=1);

use MapGenerator\HeightmapApi\Controller\EnqueueHeightmapController;

require __DIR__ . '/../vendor/autoload.php';

$controller = new EnqueueHeightmapController();

$controller->handleRequest();