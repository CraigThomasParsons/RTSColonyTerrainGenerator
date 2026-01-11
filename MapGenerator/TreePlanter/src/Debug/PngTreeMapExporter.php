<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Debug;

/**
 * PngTreeMapExporter
 *
 * Writes a PNG debug image representing vegetation placement.
 *
 * Legend:
 * - Black pixel  : empty tile
 * - Green pixel  : tree (non-bush)
 * - Olive pixel  : bush
 *
 * Notes:
 * - 1 pixel == 1 tile
 * - Reads directly from mutated tiles
 * - Never throws: debug output must not break the pipeline
 */
final class PngTreeMapExporter
{
    /**
     * Export vegetation placement as a PNG image.
     *
     * @param array<int, array<string, mixed>> $tiles
     * @param int $mapWidthInCells
     * @param int $mapHeightInCells
     * @param string $outputFile
     */
    public function export(
        array $tiles,
        int $mapWidthInCells,
        int $mapHeightInCells,
        string $outputFile
    ): void {
        // ------------------------------------------------------------
        // Ensure GD extension is available
        // ------------------------------------------------------------
        if (extension_loaded('gd') === false) {
            // Debug output must never break the pipeline
            return;
        }

        // ------------------------------------------------------------
        // Create image
        // ------------------------------------------------------------
        $image = imagecreatetruecolor(
            $mapWidthInCells,
            $mapHeightInCells
        );

        if ($image === false) {
            return;
        }

        // ------------------------------------------------------------
        // Allocate colors
        // ------------------------------------------------------------
        $colorEmpty = imagecolorallocate($image, 0, 0, 0);
        $colorTree  = imagecolorallocate($image, 0, 200, 0);
        $colorBush  = imagecolorallocate($image, 120, 140, 0);

        if (
            $colorEmpty === false ||
            $colorTree === false ||
            $colorBush === false
        ) {
            imagedestroy($image);
            return;
        }

        // ------------------------------------------------------------
        // Fill background
        // ------------------------------------------------------------
        imagefill($image, 0, 0, $colorEmpty);

        // ------------------------------------------------------------
        // Plot vegetation from tiles
        // ------------------------------------------------------------
        foreach ($tiles as $tile) {
            if (
                isset($tile['x']) === false ||
                isset($tile['y']) === false
            ) {
                continue;
            }

            $x = (int)$tile['x'];
            $y = (int)$tile['y'];

            if (
                $x < 0 ||
                $y < 0 ||
                $x >= $mapWidthInCells ||
                $y >= $mapHeightInCells
            ) {
                continue;
            }

            if (isset($tile['decorations']['tree']) === false) {
                continue;
            }

            $treeType = $tile['decorations']['tree'];

            if ($treeType === 'bush') {
                imagesetpixel($image, $x, $y, $colorBush);
            } else {
                imagesetpixel($image, $x, $y, $colorTree);
            }
        }

        // ------------------------------------------------------------
        // Ensure output directory exists
        // ------------------------------------------------------------
        $directory = dirname($outputFile);

        if (is_dir($directory) === false) {
            mkdir($directory, 0777, true);
        }

        // ------------------------------------------------------------
        // Write PNG
        // ------------------------------------------------------------
        imagepng($image, $outputFile);
        imagedestroy($image);
    }
}
