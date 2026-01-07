<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Vegetation;

/**
 * Calculates vegetation suitability scores for tiles.
 *
 * This class answers:
 * "Given terrain, weather, and local competition,
 *  how suitable is this tile for tree growth?"
 *
 * It does NOT:
 * - Place trees
 * - Choose tree types
 * - Modify tiles
 */
final class VegetationSuitabilityCalculator
{
    /**
     * Determine whether a tile is eligible for tree growth.
     *
     * @param array $tile
     * @return bool
     */
    public function tileCanSupportTrees(array $tile): bool
    {
        if (!isset($tile['tile_type'])) {
            return false;
        }

        if ($tile['tile_type'] !== 'grass' && $tile['tile_type'] !== 'dirt') {
            return false;
        }

        if (!isset($tile['height'])) {
            return false;
        }

        if ($tile['height'] < 1.5) {
            return false;
        }

        return true;
    }

    /**
     * Calculate a suitability score between 0.0 and 1.0.
     *
     * @param array $tile
     * @param array $weather
     * @param int $nearbyTreeCount
     * @return float
     */
    public function calculateSuitability(
        array $tile,
        array $weather,
        int $nearbyTreeCount
    ): float {
        $suitabilityScore = 0.0;

        if ($tile['tile_type'] === 'grass') {
            $suitabilityScore = 0.60;
        }

        if ($tile['tile_type'] === 'dirt') {
            $suitabilityScore = 0.40;
        }

        if ($tile['height'] < 2.0) {
            $suitabilityScore *= 0.55;
        }

        if ($tile['height'] > 6.0) {
            $suitabilityScore *= 0.65;
        }

        $meanRainfall = 0.5;
        $meanTemperature = 0.5;
        $windExposure = 0.5;
        $frostRisk = 0.5;

        if (isset($weather['mean_rainfall'])) {
            $meanRainfall = (float)$weather['mean_rainfall'];
        }

        if (isset($weather['mean_temperature'])) {
            $meanTemperature = (float)$weather['mean_temperature'];
        }

        if (isset($weather['wind_exposure'])) {
            $windExposure = (float)$weather['wind_exposure'];
        }

        if (isset($weather['frost_risk'])) {
            $frostRisk = (float)$weather['frost_risk'];
        }

        $suitabilityScore *=
            $this->linearInterpolate(0.55, 1.30, $meanRainfall);

        $suitabilityScore *=
            $this->linearInterpolate(1.15, 0.70, $windExposure);

        $suitabilityScore *=
            $this->linearInterpolate(1.05, 0.60, $frostRisk);

        if ($meanTemperature < 0.35) {
            $suitabilityScore *= 0.85;
        }

        $densityPenalty = 1.0 - ($nearbyTreeCount * 0.12);

        if ($densityPenalty < 0.18) {
            $densityPenalty = 0.18;
        }

        $suitabilityScore *= $densityPenalty;

        if ($suitabilityScore < 0.0) {
            $suitabilityScore = 0.0;
        }

        if ($suitabilityScore > 1.0) {
            $suitabilityScore = 1.0;
        }

        return $suitabilityScore;
    }

    /**
     * Linearly interpolate between two values.
     *
     * @param float $minimum
     * @param float $maximum
     * @param float $factor
     * @return float
     */
    private function linearInterpolate(
        float $minimum,
        float $maximum,
        float $factor
    ): float {
        if ($factor < 0.0) {
            $factor = 0.0;
        }

        if ($factor > 1.0) {
            $factor = 1.0;
        }

        return $minimum + ($maximum - $minimum) * $factor;
    }
}
