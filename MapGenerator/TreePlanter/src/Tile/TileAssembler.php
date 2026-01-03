<?php
declare(strict_types=1);

namespace RTSColonyTerrainGenerator\TreePlanter\Tile;

use InvalidArgumentException;
use RuntimeException;

/**
 * TileAssembler
 * 
 * Assembles in-memory tile array by merging .maptiles and .weather artifacts.
 * This is the FIRST stage in the pipeline that creates a unified tile representation.
 * 
 * Responsibilities:
 * - Read .maptiles artifact (terrain geometry)
 * - Read .weather artifact (climate analysis)
 * - Merge both into a structured tile array
 * - Return normalized tile array
 * 
 * Does NOT:
 * - Modify terrain or weather data
 * - Use randomness
 * - Write files
 * - Make assumptions about tile order
 */
class TileAssembler
{
    /**
     * Assemble tiles from maptiles and weather artifacts.
     * 
     * @param string $maptilesPath Absolute path to .maptiles artifact
     * @param string $weatherPath Absolute path to .weather artifact
     * @param int $expectedWidth Expected map width in cells
     * @param int $expectedHeight Expected map height in cells
     * @return array<int, array<string, mixed>> Indexed tile array
     * @throws InvalidArgumentException If files don't exist or are malformed
     * @throws RuntimeException If parsing fails or tile count mismatches
     */
    public function assemble(
        string $maptilesPath,
        string $weatherPath,
        int $expectedWidth,
        int $expectedHeight
    ): array {
        // Validate paths exist
        if (!file_exists($maptilesPath)) {
            throw new InvalidArgumentException(
                "Maptiles artifact not found: {$maptilesPath}"
            );
        }

        if (!file_exists($weatherPath)) {
            throw new InvalidArgumentException(
                "Weather artifact not found: {$weatherPath}"
            );
        }

        // Load maptiles artifact
        $maptilesContent = file_get_contents($maptilesPath);
        if ($maptilesContent === false) {
            throw new RuntimeException(
                "Failed to read maptiles artifact: {$maptilesPath}"
            );
        }

        $maptilesData = json_decode($maptilesContent, true);
        if ($maptilesData === null) {
            throw new RuntimeException(
                "Failed to parse maptiles JSON: {$maptilesPath}"
            );
        }

        // Load weather artifact
        $weatherContent = file_get_contents($weatherPath);
        if ($weatherContent === false) {
            throw new RuntimeException(
                "Failed to read weather artifact: {$weatherPath}"
            );
        }

        $weatherData = json_decode($weatherContent, true);
        if ($weatherData === null) {
            throw new RuntimeException(
                "Failed to parse weather JSON: {$weatherPath}"
            );
        }

        // Validate maptiles structure
        if (!isset($maptilesData['tiles']) || !is_array($maptilesData['tiles'])) {
            throw new RuntimeException(
                "Maptiles artifact missing 'tiles' array: {$maptilesPath}"
            );
        }

        $maptiles = $maptilesData['tiles'];

        // Build weather lookup table by position
        $weatherByPosition = $this->buildWeatherLookup($weatherData);

        // Expected tile count
        $expectedTileCount = $expectedWidth * $expectedHeight;

        // Assemble unified tiles
        $tiles = [];

        foreach ($maptiles as $maptile) {
            // Validate tile structure
            if (!isset($maptile['x']) || !isset($maptile['y']) || !isset($maptile['terrain'])) {
                throw new RuntimeException(
                    "Maptile missing required fields (x, y, terrain): {$maptilesPath}"
                );
            }

            $x = (int)$maptile['x'];
            $y = (int)$maptile['y'];
            $terrain = (string)$maptile['terrain'];

            // Lookup weather for this position
            $positionKey = $this->buildPositionKey($x, $y);
            $weatherForTile = $weatherByPosition[$positionKey] ?? null;

            // Build unified tile structure
            $tile = [
                'x' => $x,
                'y' => $y,
                'terrain' => $terrain,
                'weather' => $weatherForTile,
                'decorations' => []
            ];

            $tiles[] = $tile;
        }

        // Validate tile count
        $actualTileCount = count($tiles);
        if ($actualTileCount !== $expectedTileCount) {
            throw new RuntimeException(
                "Tile count mismatch. Expected: {$expectedTileCount}, Actual: {$actualTileCount}"
            );
        }

        return $tiles;
    }

    /**
     * Build weather lookup table indexed by position key.
     * 
     * @param array<string, mixed> $weatherData Weather artifact data
     * @return array<string, array<string, mixed>> Weather indexed by position
     */
    private function buildWeatherLookup(array $weatherData): array
    {
        $weatherByPosition = [];

        if (!isset($weatherData['tiles']) || !is_array($weatherData['tiles'])) {
            // Weather data may not have tiles array - return empty lookup
            return $weatherByPosition;
        }

        foreach ($weatherData['tiles'] as $weatherTile) {
            if (!isset($weatherTile['x']) || !isset($weatherTile['y'])) {
                // Skip malformed weather tiles
                continue;
            }

            $x = (int)$weatherTile['x'];
            $y = (int)$weatherTile['y'];
            $key = $this->buildPositionKey($x, $y);

            $weatherByPosition[$key] = $weatherTile;
        }

        return $weatherByPosition;
    }

    /**
     * Build a position key for lookups.
     * 
     * @param int $x X coordinate
     * @param int $y Y coordinate
     * @return string Position key in format "x,y"
     */
    private function buildPositionKey(int $x, int $y): string
    {
        return "{$x},{$y}";
    }
}