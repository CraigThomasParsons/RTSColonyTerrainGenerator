<?php

namespace RTSColonyTerrainGenerator\TreePlanter\Engine;

use RTSColonyTerrainGenerator\TreePlanter\World\TreePlacement;
use RTSColonyTerrainGenerator\TreePlanter\World\TreePlacementResult;
use RTSColonyTerrainGenerator\TreePlanter\Tile\TileAssembler;

final class TreePlacementEngine
{
    public function __construct(
        private readonly int $seed
    ) {}

    public function run(TileAssembler $tiles): TreePlacementResult
    {
        mt_srand($this->seed);

        $result = new TreePlacementResult();

        foreach ($tiles->all() as $tile) {
            if (!$this->tileCanHaveTree($tile)) {
                continue;
            }

            if (!$this->rollTreeChance($tile)) {
                continue;
            }

            $treeType = $this->selectTreeType($tile);

            $result->add(
                new TreePlacement(
                    $tile->x,
                    $tile->y,
                    $treeType
                )
            );
        }

        return $result;
    }

    private function tileCanHaveTree($tile): bool
    {
        // Minimal, conservative rules
        if ($tile->isWater()) return false;
        if ($tile->isMountain()) return false;
        if ($tile->isRoad()) return false;

        return true;
    }

    private function rollTreeChance($tile): bool
    {
        // VERY rough for now — we refine later
        $chance = match ($tile->biome) {
            'forest' => 0.70,
            'plains' => 0.15,
            'swamp'  => 0.35,
            default  => 0.05,
        };

        return mt_rand() / mt_getrandmax() < $chance;
    }

    private function selectTreeType($tile): string
    {
        return match ($tile->biome) {
            'forest' => 'oak',
            'swamp'  => 'mangrove',
            default  => 'scrub',
        };
    }
}
