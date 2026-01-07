<?php

declare(strict_types=1);

namespace MapGenerator\TreePlanter\Logging;

/**
 * JSONL logger for MapGenerator pipeline compatibility.
 *
 * Writes structured logs to logs/jobs/{job_id}/treeplanter.log.jsonl
 * in the same format as Heightmap/Tiler/Weather, so mapgenctl TUI can display them.
 *
 * This class is intentionally minimal and boring. It exists solely to make
 * TreePlanter observable in the TUI.
 *
 * Design Decisions:
 * - Matches the exact JSONL schema used by Tiler and Weather stages
 * - Writes logs incrementally (append-only) for crash safety
 * - Does NOT buffer or batch writes
 * - Does NOT throw on write failure (logging must never break the pipeline)
 */
final class StageLogger
{
    private string $jobIdentifier;
    private string $stageName;
    private string $logFilePath;

    /**
     * Create a new logger for the given job identifier.
     *
     * The log file path is resolved from MAPGEN_LOG_ROOT environment variable.
     * If not set, defaults to ./logs relative to the working directory.
     *
     * @param string $jobIdentifier The job identifier to scope logs to.
     */
    public function __construct(string $jobIdentifier)
    {
        $this->jobIdentifier = $jobIdentifier;
        $this->stageName = 'treeplanter';

        // Resolve logs root directory from environment
        $logRootDirectory = getenv('MAPGEN_LOG_ROOT');

        // Fall back to local logs directory if environment variable is not set
        if ($logRootDirectory === false || $logRootDirectory === '') {
            $logRootDirectory = './logs';
        }

        // Construct the per-job log directory path
        $jobLogDirectory = $logRootDirectory . '/jobs/' . $jobIdentifier;

        // Create the job log directory if it does not exist
        $directoryExistenceCheck = is_dir($jobLogDirectory);
        if ($directoryExistenceCheck === false) {
            // mkdir third parameter enables recursive directory creation
            $createDirectoriesRecursively = true;
            mkdir($jobLogDirectory, 0755, $createDirectoriesRecursively);
        }

        // Store the full path to the JSONL log file
        $this->logFilePath = $jobLogDirectory . '/treeplanter.log.jsonl';
    }

    /**
     * Log an INFO level message.
     *
     * Use for normal progress and milestone events.
     *
     * @param string $eventName Short event identifier (e.g., "stage_start")
     * @param string $message Human-readable description of the event
     */
    public function info(string $eventName, string $message): void
    {
        $this->writeLogEntry('INFO', $eventName, $message);
    }

    /**
     * Log a WARN level message.
     *
     * Use for unusual but non-fatal conditions.
     *
     * @param string $eventName Short event identifier (e.g., "missing_input")
     * @param string $message Human-readable description of the warning
     */
    public function warn(string $eventName, string $message): void
    {
        $this->writeLogEntry('WARN', $eventName, $message);
    }

    /**
     * Log an ERROR level message.
     *
     * Use for failures that cause or explain stage termination.
     *
     * @param string $eventName Short event identifier (e.g., "stage_failed")
     * @param string $message Human-readable description of the error
     */
    public function error(string $eventName, string $message): void
    {
        $this->writeLogEntry('ERROR', $eventName, $message);
    }

    /**
     * Write a log entry to the JSONL file.
     *
     * Each log entry is a single JSON object on its own line.
     * The schema matches Tiler and Weather stages for TUI compatibility.
     *
     * @param string $logLevel Log level (INFO, WARN, ERROR)
     * @param string $eventName Short event identifier
     * @param string $message Human-readable description
     */
    private function writeLogEntry(
        string $logLevel,
        string $eventName,
        string $message
    ): void {
        // Build the log entry structure matching the pipeline schema
        $logEntry = [
            'ts' => (int)(microtime(true) * 1000),
            'stage' => $this->stageName,
            'job_id' => $this->jobIdentifier,
            'level' => $logLevel,
            'event' => $eventName,
            'msg' => $message,
        ];

        // Encode the log entry as JSON
        $jsonEncodedEntry = json_encode($logEntry, JSON_UNESCAPED_SLASHES);

        // Skip writing if JSON encoding fails (should never happen with valid strings)
        if ($jsonEncodedEntry === false) {
            return;
        }

        // Append the log entry to the file with file locking for concurrency safety
        $appendToFile = FILE_APPEND | LOCK_EX;
        file_put_contents(
            $this->logFilePath,
            $jsonEncodedEntry . PHP_EOL,
            $appendToFile
        );
    }
}
