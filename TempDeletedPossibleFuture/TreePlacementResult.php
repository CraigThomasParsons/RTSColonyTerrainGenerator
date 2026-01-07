<?php

namespace RTSColonyTerrainGenerator\TreePlanter\World;

final class TreePlacementResult
{
    /** @var TreePlacement[] */
    private array $placements = [];

    public function add(TreePlacement $placement): void
    {
        $this->placements[] = $placement;
    }

    /** @return TreePlacement[] */
    public function all(): array
    {
        return $this->placements;
    }
}
