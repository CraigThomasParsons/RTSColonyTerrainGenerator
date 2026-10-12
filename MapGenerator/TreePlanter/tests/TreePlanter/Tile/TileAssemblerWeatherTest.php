<?php

declare(strict_types=1);

namespace Tests\TreePlanter\Tile;

use MapGenerator\TreePlanter\Tile\TileAssembler;
use PHPUnit\Framework\TestCase;

/**
 * Characterisation tests for weather decoding, driven by the committed golden fixtures.
 *
 * The `.weather` artifact is written planar by the Rust WeatherAnalyses stage: every slope,
 * then every flow byte, then every basin id. It was read interleaved — slope, flow and basin
 * per cell. Both layouts consume `16 + width * height * 7` bytes, so the size guard passed
 * and the reader silently produced garbage: 1111 of 4096 flow values fell outside the legal
 * 0-8 direction range, and basin ids reached 4.26 billion.
 *
 * These assertions are deliberately about properties the artifact must satisfy rather than
 * about specific decoded values. A test that pinned exact numbers would have to be rewritten
 * by whoever next touches the format, which is how a suite stops being trusted. Legality of
 * every flow direction is the property that distinguishes the two layouts, so it is the
 * property worth asserting.
 */
final class TileAssemblerWeatherTest extends TestCase
{
    /** Flow is a D8 direction: 0 for a local minimum, 1-8 for the eight neighbours. */
    private const int MAXIMUM_FLOW_DIRECTION = 8;

    /**
     * Locate a golden job directory and return its artifact paths.
     *
     * @return array{maptiles: string, weather: string}
     */
    private function goldenJobArtifacts(): array
    {
        $goldenRoot = __DIR__ . '/../../../../../tests/fixtures/golden';
        $weatherFiles = glob($goldenRoot . '/*/*.weather');

        // A missing fixture must fail loudly: a silently skipped test is worse than none.
        self::assertNotEmpty($weatherFiles, "No golden .weather fixture found under {$goldenRoot}");

        $weatherPath = $weatherFiles[0];
        $maptilesPath = substr($weatherPath, 0, -strlen('.weather')) . '.maptiles';
        self::assertFileExists($maptilesPath);

        return ['maptiles' => $maptilesPath, 'weather' => $weatherPath];
    }

    /**
     * Read the grid dimensions from a `.weather` header.
     *
     * @param string $weatherPath Absolute path to the artifact
     * @return array{width: int, height: int}
     */
    private function weatherDimensions(string $weatherPath): array
    {
        $header = unpack(
            'Vmagic/vversion/Vwidth/Vheight/vlayers',
            (string) file_get_contents($weatherPath, false, null, 0, 16)
        );

        return ['width' => (int) $header['width'], 'height' => (int) $header['height']];
    }

    /**
     * Assemble the golden fixture and collect the weather attached to each tile.
     *
     * @return array<int, array<string, mixed>>
     */
    private function assembleGoldenWeather(): array
    {
        $artifacts = $this->goldenJobArtifacts();
        $dimensions = $this->weatherDimensions($artifacts['weather']);

        // Maptiles are tile-resolution; weather is cell-resolution at half the size.
        $tiles = (new TileAssembler())->assemble(
            $artifacts['maptiles'],
            $artifacts['weather'],
            $dimensions['width'] * 2,
            $dimensions['height'] * 2
        );

        $weatherPerTile = [];

        foreach ($tiles as $tile) {
            if (is_array($tile['weather'])) {
                $weatherPerTile[] = $tile['weather'];
            }
        }

        self::assertNotEmpty($weatherPerTile, 'No tile carried weather data.');

        return $weatherPerTile;
    }

    /**
     * Every decoded flow direction must be a legal D8 value.
     *
     * This is the assertion that fails under the interleaved layout and passes under the
     * planar one, so it is the regression test for the decode bug itself.
     */
    public function testEveryFlowDirectionIsLegal(): void
    {
        $illegalDirections = [];

        foreach ($this->assembleGoldenWeather() as $weather) {
            $flowDirection = (int) $weather['flow'];

            if ($flowDirection < 0 || $flowDirection > self::MAXIMUM_FLOW_DIRECTION) {
                $illegalDirections[] = $flowDirection;
            }
        }

        self::assertSame(
            [],
            array_slice($illegalDirections, 0, 10),
            sprintf(
                '%d tiles carry a flow direction outside 0-%d, which means the weather layers '
                . 'were decoded in the wrong order.',
                count($illegalDirections),
                self::MAXIMUM_FLOW_DIRECTION
            )
        );
    }

    /**
     * Basin identifiers are assigned per sink, so none can exceed the number of cells.
     *
     * Under the interleaved layout these ran into the billions; the bound is what makes
     * that failure mode visible rather than merely implausible.
     */
    public function testBasinIdentifiersAreBoundedByTheCellCount(): void
    {
        $artifacts = $this->goldenJobArtifacts();
        $dimensions = $this->weatherDimensions($artifacts['weather']);
        $cellCount = $dimensions['width'] * $dimensions['height'];

        $outOfRangeBasins = [];

        foreach ($this->assembleGoldenWeather() as $weather) {
            $basinIdentifier = (int) $weather['basin'];

            if ($basinIdentifier < 0 || $basinIdentifier > $cellCount) {
                $outOfRangeBasins[] = $basinIdentifier;
            }
        }

        self::assertSame(
            [],
            array_slice($outOfRangeBasins, 0, 10),
            sprintf(
                '%d tiles carry a basin id outside 0-%d.',
                count($outOfRangeBasins),
                $cellCount
            )
        );
    }

    /**
     * The decoded field must vary: a layout error can also flatten real data into a constant.
     */
    public function testDecodedWeatherVariesAcrossTheMap(): void
    {
        $distinctBasins = [];

        foreach ($this->assembleGoldenWeather() as $weather) {
            $distinctBasins[(int) $weather['basin']] = true;
        }

        self::assertGreaterThan(
            1,
            count($distinctBasins),
            'Every tile decoded to the same basin, so the artifact was not read as a grid.'
        );
    }
}
