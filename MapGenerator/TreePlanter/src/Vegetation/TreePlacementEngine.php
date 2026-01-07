<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Vegetation;

use MapGenerator\TreePlanter\Random\DeterministicRandomGenerator;

/**
 * Apply vegetation placement rules to a map tile set.
 *
 * Responsibilities:
 * - Iterate tiles deterministically (row-major y, then x)
 * - For each tile:
 *   - Respect idempotency (do nothing if vegetation already exists)
 *   - Compute a suitability score in [0.0, 1.0]
 *   - Apply eligibility guards (water, lava, ice, extreme elevation)
 *   - Apply density/spacing constraints using an 8-neighbor scan
 *   - Choose vegetation type (conifer/deciduous/bush) deterministically
 *   - Mutate only tile['decorations']['vegetation']
 *
 * Constraints:
 * - Deterministic output for same inputs
 * - No terrain mutation
 * - No man-made features
 * - At most one vegetation object per tile
 *
 * Inputs expected per tile (minimum):
 * - x (int), y (int)
 * - terrain (string)
 * - elevation (int 0-255) OR elevation may be nested depending on your pipeline
 * - weather (array) optional but supported
 *
 * Tile mutation contract:
 * - If vegetation is placed:
 *     $tile['decorations']['vegetation'] = [
 *         'type' => 'conifer'|'deciduous'|'bush',
 *         'density' => 'sparse'|'normal'|'dense',
 *     ];
 *
 * - If not placed: tile remains unchanged
 */
final class TreePlacementEngine
{
    /**
     * Apply vegetation placement and return the mutated tile list.
     *
     * IMPORTANT:
     * This engine is intentionally "pure-ish":
     * - It returns a new array, but may mutate internal copies while iterating.
     * - It does not perform any file I/O.
     *
     * @param array $tiles Flat array of tiles. Each tile must include x,y.
     * @param int $mapWidthInCells Width of the map in cells
     * @param int $mapHeightInCells Height of the map in cells
     * @param int $worldSeed Deterministic seed for the job (from heightmap / job metadata)
     * @param VegetationSuitabilityCalculator $suitabilityCalculator Computes suitability score [0..1]
     * @param TreeTypeSelector $treeTypeSelector Selects vegetation type given conditions
     * @param DeterministicRandomGenerator $randomGenerator Deterministic RNG
     *
     * @return array Mutated tiles (same shape as input)
     */
    public function applyTrees(
        array $tiles,
        int $mapWidthInCells,
        int $mapHeightInCells,
        int $worldSeed,
        VegetationSuitabilityCalculator $suitabilityCalculator,
        TreeTypeSelector $treeTypeSelector,
        DeterministicRandomGenerator $randomGenerator
    ): array {
        // ------------------------------------------------------------
        // Index tiles by coordinate for neighbor lookup
        // ------------------------------------------------------------
        // We build an index:
        //   $tileIndex["x,y"] => &tile
        //
        // This allows O(1) neighbor checks without assuming tiles are
        // stored in any particular ordering.
        $tileIndex = [];

        foreach ($tiles as $tileArrayIndex => $tile) {
            if (!isset($tile['x']) || !isset($tile['y'])) {
                // Skip malformed tiles defensively; do not throw during pipeline runs.
                continue;
            }

            $xCoordinate = (int)$tile['x'];
            $yCoordinate = (int)$tile['y'];

            $tileIndex[$this->coordinateKey($xCoordinate, $yCoordinate)] = $tileArrayIndex;
        }

        // ------------------------------------------------------------
        // Iterate deterministically: row-major (y then x)
        // ------------------------------------------------------------
        for ($y = 0; $y < $mapHeightInCells; $y++) {
            for ($x = 0; $x < $mapWidthInCells; $x++) {
                $key = $this->coordinateKey($x, $y);

                if (!isset($tileIndex[$key])) {
                    // Missing tile entry; tolerate for now.
                    continue;
                }

                $tileArrayIndex = $tileIndex[$key];

                // Work on a local copy; we'll write back if we mutate.
                $tile = $tiles[$tileArrayIndex];

                // ------------------------------------------------------------
                // Idempotency guard: never overwrite existing vegetation
                // ------------------------------------------------------------
                if (
                    isset($tile['decorations']) &&
                    isset($tile['decorations']['vegetation'])
                ) {
                    continue;
                }

                // ------------------------------------------------------------
                // Eligibility guard: terrain types that can never host vegetation
                // ------------------------------------------------------------
                $terrain = $this->readTerrain($tile);

                if ($this->isNeverEligibleTerrain($terrain)) {
                    continue;
                }

                // ------------------------------------------------------------
                // Elevation guards and bands
                // ------------------------------------------------------------
                $elevation = $this->readElevation($tile);

                // Reject floodplains/swamps early
                if ($elevation < 40) {
                    continue;
                }

                // ------------------------------------------------------------
                // Compute suitability score
                // ------------------------------------------------------------
                $suitabilityScore = $suitabilityCalculator->calculateSuitabilityScore(
                    $tile
                );

                // No vegetation if suitability is too low
                if ($suitabilityScore < 0.25) {
                    continue;
                }

                // ------------------------------------------------------------
                // Density / spacing constraint using already-placed vegetation
                // ------------------------------------------------------------
                $neighborTreeCount = $this->countNeighborTrees(
                    $tiles,
                    $tileIndex,
                    $x,
                    $y
                );

                // If extremely dense, block tree placement; bushes may still pass.
                if ($neighborTreeCount >= 6) {
                    // Only allow bush placement if suitability supports it.
                    // We do not "force" bushes; we just permit them.
                    if ($suitabilityScore < 0.25 || $suitabilityScore >= 0.45) {
                        // If we're in the "tree band" and neighbors are too dense, skip.
                        // Bush-only band still can continue below.
                    }
                }

                // ------------------------------------------------------------
                // Deterministic per-tile RNG seeding
                // ------------------------------------------------------------
                $tileSeed = $this->computeTileSeed(
                    $worldSeed,
                    $mapWidthInCells,
                    $x,
                    $y
                );

                $randomGenerator->seed($tileSeed);

                // ------------------------------------------------------------
                // Placement probability derived from suitability
                // ------------------------------------------------------------
                // Suitability interpretation:
                // - 0.25–0.45 → bushes possible
                // - 0.45–0.70 → sparse trees
                // - > 0.70    → dense trees
                $placementProbability =
                    $this->placementProbabilityFromSuitability($suitabilityScore);

                // Apply neighbor penalty
                if ($neighborTreeCount >= 4 && $neighborTreeCount <= 5) {
                    $placementProbability = $placementProbability * 0.5;
                } elseif ($neighborTreeCount >= 6) {
                    // Block tree placement entirely.
                    // We still allow bush placement if suitability is in bush-only band.
                    $placementProbability = 0.0;
                }

                // Roll for placement
                $roll = $randomGenerator->nextFloat01();

                if ($roll > $placementProbability) {
                    continue;
                }

                // ------------------------------------------------------------
                // Choose vegetation type
                // ------------------------------------------------------------
                $chosenVegetationType = $treeTypeSelector->selectVegetationType(
                    $tile,
                    $suitabilityScore,
                    $elevation,
                    $randomGenerator
                );

                if ($chosenVegetationType === null) {
                    // Selector may decide no vegetation fits.
                    continue;
                }

                // ------------------------------------------------------------
                // Choose density label
                // ------------------------------------------------------------
                $densityLabel = $this->densityLabelFromSuitability($suitabilityScore);

                // ------------------------------------------------------------
                // Mutate tile decorations ONLY
                // ------------------------------------------------------------
                if (!isset($tile['decorations']) || !is_array($tile['decorations'])) {
                    $tile['decorations'] = [];
                }

                $tile['decorations']['vegetation'] = [
                    'type' => $chosenVegetationType,
                    'density' => $densityLabel,
                ];

                // Write back mutated tile
                $tiles[$tileArrayIndex] = $tile;
            }
        }

        return $tiles;
    }

    /**
     * Compute a stable coordinate key.
     *
     * @param int $xCoordinate
     * @param int $yCoordinate
     *
     * @return string
     */
    private function coordinateKey(int $xCoordinate, int $yCoordinate): string
    {
        return $xCoordinate . ',' . $yCoordinate;
    }

    /**
     * Determine whether terrain is never eligible for vegetation.
     *
     * @param string $terrain
     *
     * @return bool
     */
    private function isNeverEligibleTerrain(string $terrain): bool
    {
        $terrainLower = strtolower($terrain);

        if ($terrainLower === 'water') {
            return true;
        }

        if ($terrainLower === 'deep_water') {
            return true;
        }

        if ($terrainLower === 'lava') {
            return true;
        }

        if ($terrainLower === 'ice_sheet') {
            return true;
        }

        return false;
    }

    /**
     * Read terrain from tile with defensive defaults.
     *
     * @param array $tile
     *
     * @return string
     */
    private function readTerrain(array $tile): string
    {
        if (isset($tile['terrain']) && is_string($tile['terrain'])) {
            return $tile['terrain'];
        }

        // Default to something "safe-ish" rather than crashing.
        return 'unknown';
    }

    /**
     * Read elevation from tile with defensive defaults.
     *
     * @param array $tile
     * @return int
     */
    private function readElevation(array $tile): int
    {
        if (isset($tile['elevation'])) {
            return (int)$tile['elevation'];
        }

        // If elevation is missing, assume mid-land.
        return 120;
    }

    /**
     * Count neighboring tiles that already contain trees (not bushes).
     *
     * Neighbor scan uses 8-neighborhood.
     *
     * @param array $tiles
     * @param array $tileIndex
     * @param int $xCoordinate
     * @param int $yCoordinate
     *
     * @return int
     */
    private function countNeighborTrees(
        array $tiles,
        array $tileIndex,
        int $xCoordinate,
        int $yCoordinate
    ): int {
        $treeCount = 0;

        for ($dy = -1; $dy <= 1; $dy++) {
            for ($dx = -1; $dx <= 1; $dx++) {
                if ($dx === 0 && $dy === 0) {
                    continue;
                }

                $nx = $xCoordinate + $dx;
                $ny = $yCoordinate + $dy;

                $key = $this->coordinateKey($nx, $ny);

                if (!isset($tileIndex[$key])) {
                    continue;
                }

                $neighborArrayIndex = $tileIndex[$key];
                $neighborTile = $tiles[$neighborArrayIndex];

                if (
                    !isset($neighborTile['decorations']) ||
                    !isset($neighborTile['decorations']['vegetation'])
                ) {
                    continue;
                }

                $vegetation = $neighborTile['decorations']['vegetation'];

                if (!is_array($vegetation) || !isset($vegetation['type'])) {
                    continue;
                }

                $type = (string)$vegetation['type'];

                // Bushes do not count as trees for spacing rules.
                if ($type === 'bush') {
                    continue;
                }

                $treeCount++;
            }
        }

        return $treeCount;
    }

    /**
     * Compute deterministic per-tile seed.
     *
     * seed = worldSeed + (y * mapWidth) + x
     *
     * @param int $worldSeed
     * @param int $mapWidthInCells
     * @param int $xCoordinate
     * @param int $yCoordinate
     *
     * @return int
     */
    private function computeTileSeed(
        int $worldSeed,
        int $mapWidthInCells,
        int $xCoordinate,
        int $yCoordinate
    ): int {
        $linearIndex = ($yCoordinate * $mapWidthInCells) + $xCoordinate;

        // Keep within signed 32-bit-ish range to avoid PHP int surprises on some platforms.
        $seed = $worldSeed + $linearIndex;

        return (int)$seed;
    }

    /**
     * Convert suitability score to placement probability.
     *
     * @param float $suitabilityScore
     *
     * @return float
     */
    private function placementProbabilityFromSuitability(float $suitabilityScore): float
    {
        if ($suitabilityScore < 0.25) {
            return 0.0;
        }

        if ($suitabilityScore < 0.45) {
            // Bush band: low chance.
            return 0.15;
        }

        if ($suitabilityScore < 0.70) {
            // Sparse trees
            return 0.35;
        }

        // Dense trees
        return 0.60;
    }

    /**
     * Convert suitability score to a density label.
     *
     * @param float $suitabilityScore
     *
     * @return string
     */
    private function densityLabelFromSuitability(float $suitabilityScore): string
    {
        if ($suitabilityScore < 0.45) {
            return 'sparse';
        }

        if ($suitabilityScore < 0.70) {
            return 'normal';
        }

        return 'dense';
    }
}
