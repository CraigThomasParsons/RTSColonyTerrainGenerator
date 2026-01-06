<?php

namespace Tests\Fake;

/**
 * FakeTileAssembler
 *
 * A minimal replacement for the real TileAssembler.
 *
 * PURPOSE:
 * - Provides a stable list of tiles to the engine
 * - Avoids filesystem access
 * - Avoids dependency on upstream pipeline stages
 *
 * DESIGN NOTE:
 * - We intentionally mirror only the `all()` method
 * - This protects us from accidental coupling
 */
final class FakeTileAssembler
{
    /** @var FakeTile[] */
    private array $tiles;

    /**
     * @param FakeTile[] $tiles
     */
    public function __construct(array $tiles)
    {
        $this->tiles = $tiles;
    }

    /**
     * Return all tiles for placement analysis.
     *
     * This matches the contract used by TreePlacementEngine.
     */
    public function all(): array
    {
        return $this->tiles;
    }
}
