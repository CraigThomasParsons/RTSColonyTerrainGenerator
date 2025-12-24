<?php

declare(strict_types=1);

namespace MapGenerator\HeightmapApi\Service;

/**
 * Responsible for writing heightmap job files
 */
final class HeightmapJobWriter
{
    private string $inboxDirectory;
    /**
     * initialize HeightmapJobWriter with the inboxDirectory string.
     * Setting up the instance of this class to eventually write the
     * recipe for the heightmap generator process.
     *
     * @param string $inboxDirectory
     */
    public function __construct(string $inboxDirectory)
    {
        $this->inboxDirectory = rtrim($inboxDirectory, '/');
    }

    /**
     * Write a heightmap job JSON file atomically.
     *
     * @return array
     */
    public function writeJob(
        int $mapWidthInCells,
        int $mapHeightInCells
    ): array {
        $timestampUtc = gmdate('Y-m-d\TH-i-s\Z');
        $randomSeed = random_int(1, PHP_INT_MAX);
        $jobSuffix = bin2hex(random_bytes(3));

        $jobId = "{$timestampUtc}_{$jobSuffix}";
        $jobFilename = "{$jobId}.json";

        $jobPayload = [
            'job_id' => $jobId,
            'map_width_in_cells' => $mapWidthInCells,
            'map_height_in_cells' => $mapHeightInCells,
            'random_seed' => $randomSeed,
            'requested_at_utc' => $timestampUtc,
        ];

        $finalPath = "{$this->inboxDirectory}/{$jobFilename}";
        $temporaryPath = "{$finalPath}.tmp";

        $writeResult = file_put_contents(
            $temporaryPath,
            json_encode($jobPayload, JSON_PRETTY_PRINT)
        );

        if ($writeResult === false) {
            throw new \RuntimeException('Failed to write job file');
        }

        rename($temporaryPath, $finalPath);

        return [
            'job_id' => $jobId,
            'job_file' => $jobFilename,
        ];
    }
}
