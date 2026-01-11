<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Debug;

/**
 * AsciiTreeMapExporter
 *
 * Produces a simple ASCII visualization of vegetation placement
 * directly from the mutated tile array.
 *
 * Legend:
 *   T = tree (non-bush vegetation)
 *   b = bush
 *   . = empty / no vegetation
 *
 * This exporter:
 * - Reads tiles AFTER TreePlacementEngine has run
 * - Does not care how vegetation was decided
 * - Is safe for debug / CI / human inspection
 */
final class AsciiTreeMapExporter
{
    /**
     * Export an ASCII vegetation map.
     *
     * @param array  $tiles               Flat array of tiles (mutated)
     * @param int    $mapWidthInCells     Map width
     * @param int    $mapHeightInCells    Map height
     * @param string $outputFile          Output file path
     */
    public function export(
        array $tiles,
        int $mapWidthInCells,
        int $mapHeightInCells,
        string $outputFile
    ): void {
        // ------------------------------------------------------------
        // Initialize empty grid
        // ------------------------------------------------------------
        $grid = array_fill(
            0,
            $mapHeightInCells,
            array_fill(0, $mapWidthInCells, '.')
        );

        // ------------------------------------------------------------
        // Plot vegetation from tiles
        // ------------------------------------------------------------
        foreach ($tiles as $tile) {
            if (!isset($tile['x'], $tile['y'])) {
                continue;
            }

            $x = (int)$tile['x'];
            $y = (int)$tile['y'];

            // Bounds safety — debug tools must never explode
            if (
                $x < 0 || $y < 0 ||
                $x >= $mapWidthInCells ||
                $y >= $mapHeightInCells
            ) {
                continue;
            }

            if (
                !isset($tile['decorations']) ||
                !isset($tile['decorations']['vegetation'])
            ) {
                continue;
            }

            $vegetation = $tile['decorations']['vegetation'];

            if (!is_array($vegetation) || !isset($vegetation['type'])) {
                continue;
            }

            // Bushes get a different symbol
            if ($vegetation['type'] === 'bush') {
                $grid[$y][$x] = 'b';
            } else {
                $grid[$y][$x] = 'T';
            }
        }

        // ------------------------------------------------------------
        // Write file
        // ------------------------------------------------------------
        $lines = array_map(
            fn(array $row) => implode('', $row),
            $grid
        );

        $dir = dirname($outputFile);
        if (!is_dir($dir)) {
            mkdir($dir, 0777, true);
        }

        file_put_contents(
            $outputFile,
            implode(PHP_EOL, $lines) . PHP_EOL
        );
    }
}
