<?php

namespace Tests\Fake;

/**
 * FakeTile
 *
 * A minimal stand-in for a real Tile domain object.
 *
 * PURPOSE:
 * - Used ONLY in unit tests
 * - Avoids pulling in the real Tile implementation
 * - Gives TreePlacementEngine exactly what it needs, nothing more
 *
 * IMPORTANT:
 * - This class should NEVER be used in production code
 * - If TreePlacementEngine starts requiring more data,
 *   we update this fake explicitly
 */
final class FakeTile
{
    public function __construct(
        public int $x,
        public int $y,
        public string $biome,
        private bool $water = false,
        private bool $mountain = false,
        private bool $road = false
    ) {}

    /**
     * Whether this tile represents water.
     */
    public function isWater(): bool
    {
        return $this->water;
    }

    /**
     * Whether this tile represents a mountain.
     */
    public function isMountain(): bool
    {
        return $this->mountain;
    }

    /**
     * Whether this tile contains a road.
     */
    public function isRoad(): bool
    {
        return $this->road;
    }
}