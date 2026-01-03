<?php
declare(strict_types=1);

namespace MapGenerator\TreePlanter\World;

use InvalidArgumentException;
use RuntimeException;

/**
 * WorldPayloadWriter
 *
 * Serializes assembled tiles into a deterministic .worldpayload artifact.
 *
 * Responsibilities:
 * - Validate world payload structure
 * - Write canonical JSON payload
 *
 * Does NOT:
 * - Modify tiles
 * - Perform placement logic
 * - Add randomness
 */
final class WorldPayloadWriter
{
    /**
     * Write a .worldpayload file.
     *
     * @param string $outputDirectory Absolute output directory
     * @param string $jobId Job identifier
     * @param int $width Map width in cells
     * @param int $height Map height in cells
     * @param array<int, array<string, mixed>> $tiles Assembled tiles
     *
     * @return string Absolute path to written payload
     */
    public function write(
        string $outputDirectory,
        string $jobId,
        int $width,
        int $height,
        array $tiles
    ): string {
        if (!is_dir($outputDirectory)) {
            throw new InvalidArgumentException(
                "WorldPayload output directory does not exist: {$outputDirectory}"
            );
        }

        $payload = [
            'version' => 1,
            'job_id' => $jobId,
            'map' => [
                'width_in_cells' => $width,
                'height_in_cells' => $height,
            ],
            'tiles' => array_values($tiles),
        ];

        $json = json_encode(
            $payload,
            JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES
        );

        if ($json === false) {
            throw new RuntimeException('Failed to encode world payload JSON');
        }

        $path = rtrim($outputDirectory, '/')
            . '/'
            . $jobId
            . '.worldpayload';

        if (file_put_contents($path, $json) === false) {
            throw new RuntimeException(
                "Failed to write world payload: {$path}"
            );
        }

        return $path;
    }
}
