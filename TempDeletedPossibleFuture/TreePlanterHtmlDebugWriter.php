<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Debug;

/**
 * Renders a human-readable HTML debug view of TreePlanter output.
 *
 * This class mirrors the Tiler HTML debug artifact philosophy:
 *
 * - Output is written to TreePlanter/debug/<job-id>.html
 * - Output is never archived
 * - Output is never consumed by downstream stages
 * - Output is safe to delete at any time
 *
 * The HTML grid visualizes vegetation placement only.
 * Terrain, weather, and height are intentionally not shown.
 */
final class TreePlanterHtmlDebugWriter
{
    /**
     * Write an HTML debug grid for a TreePlanter job.
     *
     * @param string $debugDirectory
     * @param string $jobIdentifier
     * @param array $tiles
     * @param int $mapWidthInCells
     * @param int $mapHeightInCells
     * @return void
     */
    public function write(
        string $debugDirectory,
        string $jobIdentifier,
        array $tiles,
        int $mapWidthInCells,
        int $mapHeightInCells
    ): void {
        // Ensure debug directory exists.
        // Debug output must never block pipeline execution.
        if (!is_dir($debugDirectory)) {
            mkdir($debugDirectory, 0777, true);
        }

        $htmlFilePath =
            rtrim($debugDirectory, '/') . '/' .
            $jobIdentifier . '.html';

        // Initialize a full grid with non-breaking spaces.
        // Every <td> must contain exactly one character.
        $grid = [];

        for ($y = 0; $y < $mapHeightInCells; $y++) {
            for ($x = 0; $x < $mapWidthInCells; $x++) {
                $grid[$y][$x] = '&nbsp;';
            }
        }

        // Populate grid based on TreePlanter decorations.
        foreach ($tiles as $tile) {
            if (!isset($tile['x']) || !isset($tile['y'])) {
                continue;
            }

            $xCoordinate = (int)$tile['x'];
            $yCoordinate = (int)$tile['y'];

            if (
                !isset($tile['decorations']) ||
                !isset($tile['decorations']['tree'])
            ) {
                continue;
            }

            $treeType = (string)$tile['decorations']['tree'];

            // Map semantic tree type to visual glyph.
            if ($treeType === 'tall') {
                $grid[$yCoordinate][$xCoordinate] = '🌲';
            } elseif ($treeType === 'canopy') {
                $grid[$yCoordinate][$xCoordinate] = '🌳';
            } elseif ($treeType === 'bush') {
                $grid[$yCoordinate][$xCoordinate] = '🌿';
            }
        }

        // Begin HTML output.
        $html = [];
        $html[] = '<!DOCTYPE html>';
        $html[] = '<html lang="en">';
        $html[] = '<head>';
        $html[] = '    <meta charset="UTF-8">';
        $html[] = '    <h1>TreePlanter Debug – ' . htmlspecialchars($jobIdentifier) . '</h1>';
        $html[] = '';
        $html[] = '    <style>';
        $html[] = '        table {';
        $html[] = '            border-collapse: collapse;';
        $html[] = '            font-family: monospace;';
        $html[] = '        }';
        $html[] = '';
        $html[] = '        td {';
        $html[] = '            width: 24px;';
        $html[] = '            height: 24px;';
        $html[] = '            text-align: center;';
        $html[] = '            vertical-align: middle;';
        $html[] = '            border: 1px solid #ddd;';
        $html[] = '        }';
        $html[] = '    </style>';
        $html[] = '</head>';
        $html[] = '<body>';
        $html[] = '';
        $html[] = '    <h1>TreePlanter Debug – ' . htmlspecialchars($jobIdentifier) . '</h1>';
        $html[] = '';
        $html[] = '';
        $html[] = '    <div style="margin-bottom: 12px;">';
        $html[] = '        <strong>Legend:</strong>';
        $html[] = '        <span style="margin-left: 12px;">🌲 Coniferous (Pine)</span>';
        $html[] = '        <span style="margin-left: 12px;">🌳 Deciduous</span>';
        $html[] = '        <span style="margin-left: 12px;">🌿 Bush</span>';
        $html[] = '        <span style="margin-left: 12px;">&nbsp; Empty</span>';
        $html[] = '    </div>';
        $html[] = '    <table>';
        $html[] = '        <tbody>';

        // Emit rows top-to-bottom, left-to-right.
        for ($y = 0; $y < $mapHeightInCells; $y++) {
            $html[] = '            <tr>';

            for ($x = 0; $x < $mapWidthInCells; $x++) {
                $html[] =
                    '                <td>' .
                    $grid[$y][$x] .
                    '</td>';
            }

            $html[] = '            </tr>';
        }

        $html[] = '        </tbody>';
        $html[] = '    </table>';
        $html[] = '';
        $html[] = '</body>';
        $html[] = '</html>';

        // Write HTML file atomically.
        file_put_contents(
            $htmlFilePath,
            implode(PHP_EOL, $html)
        );
    }
}
