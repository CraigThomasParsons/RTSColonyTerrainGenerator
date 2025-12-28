
<?php

namespace MapGenerator\TreePlanter;

final class TreePlacementEngine
{
    public function applyTrees(
        array $tiles,
        Job $job,
        DeterministicRandomGenerator $rng,
        VegetationSuitabilityCalculator $suitability,
        TreeTypeSelector $selector
    ): array {
        foreach ($tiles as &$tile) {
            // 1. calculate suitability
            // 2. roll RNG
            // 3. select tree
            // 4. mutate tile
        }

        return $tiles;
    }
}
