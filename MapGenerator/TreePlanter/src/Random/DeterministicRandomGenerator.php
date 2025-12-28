<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Random;

/**
 * Generates deterministic random values based on
 * map seed and tile coordinates.
 */
final class DeterministicRandomGenerator
{
    /**
     * Generate a deterministic float in the range [0, 1).
     *
     * @param string $mapSeed
     * @param int $xCoordinate
     * @param int $yCoordinate
     * @return float
     */
    public function generateFloat(
        string $mapSeed,
        int $xCoordinate,
        int $yCoordinate
    ): float {
        $seedString =
            $mapSeed . ':' . $xCoordinate . ':' . $yCoordinate;

        $derivedSeed = crc32($seedString);

        mt_srand($derivedSeed);

        return mt_rand() / mt_getrandmax();
    }
}
