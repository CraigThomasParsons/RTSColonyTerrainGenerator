<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Job;

/**
 * Locates complete TreePlanter jobs in inbox directories.
 *
 * A job is considered complete when:
 * - <id>.heightmap exists
 * - <id>.maptiles exists
 * - <id>.weather exists
 */
final class JobLocator
{
    private string $heightmapInboxDirectory;
    private string $maptilesInboxDirectory;
    private string $weatherInboxDirectory;

    /**
     * @param string $heightmapInboxDirectory
     * @param string $maptilesInboxDirectory
     * @param string $weatherInboxDirectory
     */
    public function __construct(
        string $heightmapInboxDirectory,
        string $maptilesInboxDirectory,
        string $weatherInboxDirectory
    ) {
        $this->heightmapInboxDirectory = $heightmapInboxDirectory;
        $this->maptilesInboxDirectory = $maptilesInboxDirectory;
        $this->weatherInboxDirectory = $weatherInboxDirectory;
    }

    /**
     * Find the next available complete job.
     *
     * @return array|null
     */
    public function findNextJob(): ?array
    {
        $maptilesFiles =
            glob($this->maptilesInboxDirectory . '/*.maptiles');

        if ($maptilesFiles === false) {
            return null;
        }

        foreach ($maptilesFiles as $maptilesFilePath) {
            $jobIdentifier =
                basename($maptilesFilePath, '.maptiles');

            $heightmapPath =
                $this->heightmapInboxDirectory . '/' .
                $jobIdentifier . '.heightmap';

            $weatherPath =
                $this->weatherInboxDirectory . '/' .
                $jobIdentifier . '.weather';

            if (is_file($heightmapPath) && is_file($weatherPath)) {
                return [
                    'job_id' => $jobIdentifier,
                    'heightmap' => $heightmapPath,
                    'maptiles' => $maptilesFilePath,
                    'weather' => $weatherPath,
                ];
            }
        }

        return null;
    }
}
