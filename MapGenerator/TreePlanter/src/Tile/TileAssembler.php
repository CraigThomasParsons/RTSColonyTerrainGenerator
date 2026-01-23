<?php
declare(strict_types=1);

namespace MapGenerator\TreePlanter\Tile;

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
    ): array
    {
        // Why: We must fail fast if the upstream artifacts are missing.
        if (!file_exists($maptilesPath)) {
            throw new InvalidArgumentException(
                "Maptiles artifact not found: {$maptilesPath}"
            );
        }

        // Why: Weather is required to assemble full tiles.
        if (!file_exists($weatherPath)) {
            throw new InvalidArgumentException(
                "Weather artifact not found: {$weatherPath}"
            );
        }

        // Why: We read the artifact once to avoid double I/O and partial reads.
        $maptilesContent = file_get_contents($maptilesPath);
        if ($maptilesContent === false) {
            throw new RuntimeException(
                "Failed to read maptiles artifact: {$maptilesPath}"
            );
        }

        // Why: Maptiles are binary MTIL in production, but JSON is still supported.
        $maptilesData = $this->parseMaptiles($maptilesContent, $maptilesPath);

        // Why: Weather artifacts are binary; JSON support is kept for tooling.
        $weatherContent = file_get_contents($weatherPath);
        if ($weatherContent === false) {
            throw new RuntimeException(
                "Failed to read weather artifact: {$weatherPath}"
            );
        }

        // Why: Parsing is centralized to keep this method readable.
        $weatherData = $this->parseWeather($weatherContent, $weatherPath);

        // Validate maptiles structure
        if (!isset($maptilesData['tiles']) || !is_array($maptilesData['tiles'])) {
            throw new RuntimeException(
                "Maptiles artifact missing 'tiles' array: {$maptilesPath}"
            );
        }

        // Why: We only proceed when tiles are structured as an array.
        $maptiles = $maptilesData['tiles'];

        // Why: Width/height let us correctly align weather data to tiles.
        $maptilesWidth = isset($maptilesData['width']) ? (int)$maptilesData['width'] : null;
        $maptilesHeight = isset($maptilesData['height']) ? (int)$maptilesData['height'] : null;

        // Why: Weather is stored as a grid; we build a fast lookup by position key.
        $weatherByPosition = $this->buildWeatherLookup($weatherData);
        $weatherWidth = isset($weatherData['width']) ? (int)$weatherData['width'] : null;
        $weatherHeight = isset($weatherData['height']) ? (int)$weatherData['height'] : null;

        // Why: The tile grid must match the expected dimensions.
        $expectedTileCount = $expectedWidth * $expectedHeight;

        // Why: We collect normalized tiles so downstream stages are deterministic.
        $tiles = [];

        foreach ($maptiles as $maptile) {
            // Why: Each tile must declare its position and terrain.
            if (!isset($maptile['x']) || !isset($maptile['y']) || !isset($maptile['terrain'])) {
                throw new RuntimeException(
                    "Maptile missing required fields (x, y, terrain): {$maptilesPath}"
                );
            }

            $tileX = (int)$maptile['x'];
            $tileY = (int)$maptile['y'];
            $terrain = (string)$maptile['terrain'];

            // Why: Weather is cell-resolution; maptiles are tile-resolution (2x).
            if ($weatherWidth !== null && $weatherHeight !== null &&
                $maptilesWidth !== null && $maptilesHeight !== null &&
                $weatherWidth * 2 === $maptilesWidth && $weatherHeight * 2 === $maptilesHeight) {
                $positionKey = $this->buildPositionKey(intdiv($tileX, 2), intdiv($tileY, 2));
            } else {
                // Why: If dimensions do not align, fall back to direct coordinates.
                $positionKey = $this->buildPositionKey($tileX, $tileY);
            }
            $weatherForTile = $weatherByPosition[$positionKey] ?? null;

            // Why: The unified tile format feeds deterministic placement logic.
            $tile = [
                'x' => $tileX,
                'y' => $tileY,
                'terrain' => $terrain,
                'weather' => $weatherForTile,
                'decorations' => []
            ];

            $tiles[] = $tile;
        }

        // Why: Mismatched counts indicate upstream artifact mismatch or corruption.
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

        // Why: Weather is optional for some pipelines; return empty lookup when absent.
        if (!isset($weatherData['tiles']) || !is_array($weatherData['tiles'])) {
            return $weatherByPosition;
        }

        foreach ($weatherData['tiles'] as $weatherTile) {
            // Why: We skip malformed rows to avoid breaking entire jobs.
            if (!isset($weatherTile['x']) || !isset($weatherTile['y'])) {
                continue;
            }

            $cellX = (int)$weatherTile['x'];
            $cellY = (int)$weatherTile['y'];
            $positionKey = $this->buildPositionKey($cellX, $cellY);

            $weatherByPosition[$positionKey] = $weatherTile;
        }

        return $weatherByPosition;
    }

    /**
     * Build a position key for lookups.
     * 
     * @param int $columnIndex X coordinate
     * @param int $rowIndex Y coordinate
     * @return string Position key in format "x,y"
     */
    private function buildPositionKey(int $columnIndex, int $rowIndex): string
    {
        return "{$columnIndex},{$rowIndex}";
    }

    /**
     * Parse maptiles artifact as binary MTIL or JSON.
     *
     * @return array<string, mixed>
     */
    private function parseMaptiles(string $content, string $path): array
    {
        // Why: MTIL indicates the binary format produced by the Tiler.
        if (strlen($content) >= 4 && substr($content, 0, 4) === "MTIL") {
            return $this->parseBinaryMaptiles($content, $path);
        }

        // Why: JSON support keeps legacy tools functional during transitions.
        $maptilesData = json_decode($content, true);
        if ($maptilesData === null) {
            throw new RuntimeException(
                "Failed to parse maptiles JSON: {$path}"
            );
        }

        return $maptilesData;
    }

    /**
     * Parse binary MTIL format written by the Tiler.
     *
     * @return array<string, mixed>
     */
    private function parseBinaryMaptiles(string $content, string $path): array
    {
        // Why: The MTIL header is 32 bytes and must be fully present.
        if (strlen($content) < 32) {
            throw new RuntimeException(
                "Maptiles file too small to contain MTIL header: {$path}"
            );
        }

        // Why: We trust the header for dimensions and counts.
        $version = unpack('V', substr($content, 4, 4))[1];
        $tileWidth = unpack('V', substr($content, 8, 4))[1];
        $tileHeight = unpack('V', substr($content, 12, 4))[1];
        $tileCount = unpack('V', substr($content, 24, 4))[1];

        // Why: A mismatch indicates corrupt or partial output.
        $expectedCount = $tileWidth * $tileHeight;
        if ($tileCount !== $expectedCount) {
            throw new RuntimeException(
                "Maptiles tile_count mismatch (header={$tileCount}, expected={$expectedCount}): {$path}"
            );
        }

        // Why: Each tile ID is a u16 and must fit exactly in the file.
        $bodyOffset = 32;
        $bodySize = $tileCount * 2;
        if (strlen($content) < $bodyOffset + $bodySize) {
            throw new RuntimeException(
                "Maptiles file truncated (need {$bodySize} bytes): {$path}"
            );
        }

        $tileIdBuffer = unpack('v*', substr($content, $bodyOffset, $bodySize));

        // Why: We expand the packed IDs into explicit tiles for the engine.
        $tiles = [];
        $tileIndex = 0;
        for ($rowIndex = 0; $rowIndex < $tileHeight; $rowIndex++) {
            for ($columnIndex = 0; $columnIndex < $tileWidth; $columnIndex++) {
                $tileId = $tileIdBuffer[++$tileIndex];
                $terrainCode = ($tileId >> 8) & 0xFF;
                $terrain = $this->terrainFromCode($terrainCode);
                $tiles[] = [
                    'x' => $columnIndex,
                    'y' => $rowIndex,
                    'terrain' => $terrain,
                ];
            }
        }

        return [
            'tiles' => $tiles,
            'version' => $version,
            'width' => (int)$tileWidth,
            'height' => (int)$tileHeight,
        ];
    }

    /**
     * Map terrain code to terrain string.
     *
     * @return string
     */
    private function terrainFromCode(int $terrainCode): string
    {
        return match ($terrainCode) {
            0 => 'water',
            1 => 'grass',
            2 => 'mountain',
            3 => 'rock',
            default => 'unknown',
        };
    }

    /**
     * Parse weather artifact as binary or JSON.
     *
     * @return array<string, mixed>
     */
    private function parseWeather(string $content, string $path): array
    {
        // Why: JSON is used by some tooling; binary is used in production.
        $trimmed = ltrim($content);
        if ($trimmed !== '' && ($trimmed[0] === '{' || $trimmed[0] === '[')) {
            $weatherData = json_decode($content, true);
            if ($weatherData === null) {
                throw new RuntimeException(
                    "Failed to parse weather JSON: {$path}"
                );
            }
            return $weatherData;
        }

        // Why: The weather binary header is 16 bytes and must be intact.
        if (strlen($content) < 16) {
            throw new RuntimeException(
                "Weather file too small to contain header: {$path}"
            );
        }

        $headerData = unpack('Vmagic/vversion/Vwidth/Vheight/vlayers', substr($content, 0, 16));
        $gridWidth = (int)$headerData['width'];
        $gridHeight = (int)$headerData['height'];
        $cellCount = $gridWidth * $gridHeight;
        $expectedSize = 16 + ($cellCount * 7);

        // Why: Truncated binaries cannot be parsed safely.
        if (strlen($content) < $expectedSize) {
            throw new RuntimeException(
                "Weather file truncated (need {$expectedSize} bytes): {$path}"
            );
        }

        // Why: We expand the packed layers into explicit tile metadata.
        $tiles = [];
        $offset = 16;
        for ($rowIndex = 0; $rowIndex < $gridHeight; $rowIndex++) {
            for ($columnIndex = 0; $columnIndex < $gridWidth; $columnIndex++) {
                $rawSlope = unpack('v', substr($content, $offset, 2))[1];
                $slope = $rawSlope > 32767 ? $rawSlope - 65536 : $rawSlope;
                $offset += 2;

                $flow = unpack('C', substr($content, $offset, 1))[1];
                $offset += 1;

                $basin = unpack('V', substr($content, $offset, 4))[1];
                $offset += 4;

                $tiles[] = [
                    'x' => $columnIndex,
                    'y' => $rowIndex,
                    'slope' => $slope,
                    'flow' => $flow,
                    'basin' => $basin,
                ];
            }
        }

        return [
            'tiles' => $tiles,
            'version' => (int)$headerData['version'],
            'width' => $gridWidth,
            'height' => $gridHeight,
            'layers' => (int)$headerData['layers'],
        ];
    }
}