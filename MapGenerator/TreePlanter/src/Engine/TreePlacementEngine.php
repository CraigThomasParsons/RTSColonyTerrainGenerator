<?php

namespace MapGenerator\TreePlanter\Engine;

final class TreePlacementEngine
{
    public function __construct(
        private readonly int $seed = 12345
    ) {
        // Why: A fixed seed keeps placement deterministic across runs.
    }

    /**
     * @param array<int, array> $tiles
     * @return array Modified tiles with trees added
     */
    public function run(array $tiles): array
    {
        // Why: We seed RNG once to keep deterministic output for a given job.
        mt_srand($this->seed);

        foreach ($tiles as &$tile) {
            // Why: Some terrains should never contain trees.
            if (!$this->tileCanHaveTree($tile)) {
                continue;
            }

            // Why: Even eligible tiles should not always receive trees.
            if (!$this->rollTreeChance($tile)) {
                continue;
            }

            $treeType = $this->selectTreeType($tile);

            // Why: Tree decorations are stored with the tile for downstream usage.
            $tile['decorations'][] = [
                'type' => 'tree',
                'variety' => $treeType,
            ];
        }

        return $tiles;
    }

    private function tileCanHaveTree(array $tile): bool
    {
        $terrain = $tile['terrain'] ?? 'unknown';

        // Why: Water bodies do not accept trees.
        if ($terrain === 'water' || $terrain === 'ocean' || $terrain === 'river') {
            return false;
        }

        // Why: Rocky and alpine terrain should remain clear of trees.
        if ($terrain === 'mountain' || $terrain === 'rock' || $terrain === 'snow_peak') {
            return false;
        }

        return true;
    }

    private function rollTreeChance(array $tile): bool
    {
        $terrain = $tile['terrain'] ?? 'unknown';

        // Why: Each terrain type has a different natural tree density.
        $chance = match ($terrain) {
            'forest' => 0.70,
            'jungle' => 0.80,
            'taiga'  => 0.60,
            'grass'  => 0.15, // Plains/Grass
            'swamp'  => 0.35,
            'desert' => 0.01, // Oasis?
            default  => 0.05,
        };

        return (mt_rand() / mt_getrandmax()) < $chance;
    }

    private function selectTreeType(array $tile): string
    {
        $terrain = $tile['terrain'] ?? 'unknown';

        return match ($terrain) {
            'forest' => 'oak',
            'jungle' => 'mahogany',
            'taiga'  => 'pine',
            'swamp'  => 'mangrove',
            'desert' => 'palm',
            'grass'  => 'oak',
            default  => 'scrub',
        };
    }
}