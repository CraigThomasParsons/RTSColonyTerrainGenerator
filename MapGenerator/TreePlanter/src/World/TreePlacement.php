<?php

namespace RTSColonyTerrainGenerator\TreePlanter\World;

final class TreePlacement
{
    public function __construct(
        public readonly int $x,
        public readonly int $y,
        public readonly string $treeType
    ) {}
}
