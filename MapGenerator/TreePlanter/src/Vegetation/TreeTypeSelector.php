<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Vegetation;

/**
 * Selects an appropriate tree type for a tile
 * once placement has been approved.
 */
final class TreeTypeSelector
{
    /**
     * Choose a tree type based on terrain and weather.
     *
     * @param array $tile
     * @param array $weather
     * @param float $randomValue
     * @return string
     */
    public function chooseTreeType(
        array $tile,
        array $weather,
        float $randomValue
    ): string {
        $treeTypeWeights = [
            'canopy' => 0.45,
            'bush' => 0.35,
            'tall' => 0.20,
        ];

        if (isset($tile['terrain_layer'])) {
            if ($tile['terrain_layer'] === 'pine_mountain') {
                $treeTypeWeights['tall'] = 0.8;
                $treeTypeWeights['canopy'] = 0.2;
            }

            if ($tile['terrain_layer'] === 'coastal_lowland') {
                $treeTypeWeights['canopy'] = 0.6;
                $treeTypeWeights['bush'] = 0.4;
            }
        }

        if (
            $tile['height'] >= 5.0 ||
            (
                isset($weather['mean_temperature']) &&
                $weather['mean_temperature'] < 0.4
            )
        ) {
            $treeTypeWeights['tall'] += 0.2;
        }

        $totalWeight = 0.0;

        foreach ($treeTypeWeights as $weight) {
            $totalWeight += $weight;
        }

        $selectionPoint = $randomValue * $totalWeight;
        $runningWeight = 0.0;

        foreach ($treeTypeWeights as $treeType => $weight) {
            $runningWeight += $weight;

            if ($selectionPoint <= $runningWeight) {
                return $treeType;
            }
        }

        return 'bush';
    }
}
