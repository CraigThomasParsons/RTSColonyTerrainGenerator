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
        // Why: We prefer the newest complete job to avoid reprocessing old artifacts.
        $maptilesFiles =
            glob($this->maptilesInboxDirectory . '/*.maptiles');

        // Why: If the directory cannot be read, we cannot safely pick any job.
        if ($maptilesFiles === false) {
            return null;
        }

        // Why: Build candidates first so we can pick the newest one deterministically.
        $candidates = [];

        foreach ($maptilesFiles as $maptilesFilePath) {
            $jobIdentifier =
                basename($maptilesFilePath, '.maptiles');

            $heightmapPath =
                $this->heightmapInboxDirectory . '/' .
                $jobIdentifier . '.heightmap';

            $weatherPath =
                $this->weatherInboxDirectory . '/' .
                $jobIdentifier . '.weather';

            // Why: A job is only complete when all three artifacts exist.
            if (!is_file($heightmapPath) || !is_file($weatherPath)) {
                continue;
            }

            // Why: Use the newest mtime among required artifacts as the job's freshness.
            $maptilesMtime = filemtime($maptilesFilePath);
            $heightmapMtime = filemtime($heightmapPath);
            $weatherMtime = filemtime($weatherPath);

            // Why: If we cannot reliably compare mtimes, skip this candidate to avoid stale picks.
            if ($maptilesMtime === false || $heightmapMtime === false || $weatherMtime === false) {
                continue;
            }

            $freshness = max($maptilesMtime, $heightmapMtime, $weatherMtime);

            $candidates[] = [
                'job_id' => $jobIdentifier,
                'heightmap' => $heightmapPath,
                'maptiles' => $maptilesFilePath,
                'weather' => $weatherPath,
                'mtime' => $freshness,
            ];
        }

        // Why: If nothing is complete, return null to indicate idle state.
        if (count($candidates) === 0) {
            return null;
        }

        usort(
            $candidates,
            static function (array $firstCandidate, array $secondCandidate): int {
                // Why: Sort newest first so the most recent job is processed.
                return $secondCandidate['mtime'] <=> $firstCandidate['mtime'];
            }
        );

        // Why: The first entry after sorting is the freshest complete job.
        $selected = $candidates[0];

        return [
            'job_id' => $selected['job_id'],
            'heightmap' => $selected['heightmap'],
            'maptiles' => $selected['maptiles'],
            'weather' => $selected['weather'],
        ];
    }
}
