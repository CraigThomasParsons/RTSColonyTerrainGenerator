<?php

namespace MapGenerator\TreePlanter\Engine;

final class TreePlacementEngine
{
    public function __construct(
        private readonly int $seed = 12345
    ) {}

    /**
     * @param array<int, array> $tiles
     * @return array Modified tiles with trees added
     */
    public function run(array $tiles): array
    {
        mt_srand($this->seed);

        foreach ($tiles as &$tile) {
            if (!$this->tileCanHaveTree($tile)) {
                continue;
            }

            if (!$this->rollTreeChance($tile)) {
                continue;
            }

            $treeType = $this->selectTreeType($tile);

            // Add tree to decorations
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

        // Water checks
        if ($terrain === 'water' || $terrain === 'ocean' || $terrain === 'river') {
            return false;
        }

        // Mountain/Rock checks
        if ($terrain === 'mountain' || $terrain === 'rock' || $terrain === 'snow_peak') {
            return false;
        }

        return true;
    }

    private function rollTreeChance(array $tile): bool
    {
        $terrain = $tile['terrain'] ?? 'unknown';

        // Map terrain to tree probability
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
