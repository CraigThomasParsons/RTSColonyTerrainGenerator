package fswatch

import (
	"fmt"
	"mapgen-web/internal/jobs"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// Paths are the pipeline stage directories we monitor.
// Can be overridden via PIPELINE_ROOT environment variable.
// Defaults to relative paths suitable for Docker.
var (
	pipelineRootPath  = getEnv("PIPELINE_ROOT", "./MapGenerator")
	HeightmapInbox    = filepath.Join(pipelineRootPath, "Heightmap/inbox")
	HeightmapOutbox   = filepath.Join(pipelineRootPath, "Heightmap/outbox")
	TilerInbox        = filepath.Join(pipelineRootPath, "Tiler/inbox")
	TilerOutbox       = filepath.Join(pipelineRootPath, "Tiler/outbox")
	WeatherInbox      = filepath.Join(pipelineRootPath, "WeatherAnalyses/inbox")
	WeatherOutbox     = filepath.Join(pipelineRootPath, "WeatherAnalyses/outbox")
	TreeplanterInbox  = filepath.Join(pipelineRootPath, "TreePlanter/inbox")
	TreeplanterOutbox = filepath.Join(pipelineRootPath, "TreePlanter/outbox")
)

// getEnv returns an environment variable or a default value
func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

// Watcher periodically polls the pipeline directories for file changes.
// It updates job states based on file locations.
type Watcher struct {
	registry *jobs.Registry
	lastSeen map[string]time.Time // filename -> last observed time
}

// NewWatcher creates a new filesystem watcher.
func NewWatcher(registry *jobs.Registry) *Watcher {
	return &Watcher{
		registry: registry,
		lastSeen: make(map[string]time.Time),
	}
}

// Poll checks all pipeline directories once and updates job states.
// This is a simple polling approach; for production, use inotify.
func (watcher *Watcher) Poll() error {
	// Define all directories to check: (dir, stage, location)
	stageChecks := []struct {
		directoryPath string
		stageName     string
		locationName  string
	}{
		{HeightmapInbox, "heightmap", "inbox"},
		{HeightmapOutbox, "heightmap", "outbox"},
		{TilerInbox, "tiler", "inbox"},
		{TilerOutbox, "tiler", "outbox"},
		{WeatherInbox, "weather", "inbox"},
		{WeatherOutbox, "weather", "outbox"},
		{TreeplanterInbox, "treeplanter", "inbox"},
		{TreeplanterOutbox, "treeplanter", "outbox"},
	}

	for _, stageCheck := range stageChecks {
		if err := watcher.pollDir(stageCheck.directoryPath, stageCheck.stageName, stageCheck.locationName); err != nil {
			// Log but continue; one directory should not block others
			fmt.Printf("error polling %s: %v\n", stageCheck.directoryPath, err)
		}
	}

	return nil
}

// pollDir scans a single directory and updates jobs accordingly.
func (watcher *Watcher) pollDir(directoryPath, stageName, locationName string) error {
	entries, err := os.ReadDir(directoryPath)
	if err != nil {
		// Directory may not exist yet; that's fine
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	currentFiles := make(map[string]bool)

	for _, entry := range entries {
		if entry.IsDir() {
			continue // Skip directories
		}

		filename := entry.Name()
		currentFiles[filename] = true

		// Extract job ID from filename (typically the base name without extension)
		jobID := extractJobID(filename)
		if jobID == "" {
			continue // Skip files we can't identify
		}

		// If this is a new file, we may need to update the job state
		_, wasKnown := watcher.lastSeen[filename]
		observedAt := time.Now()
		watcher.lastSeen[filename] = observedAt

		// Only update if file is new or significantly changed
		if !wasKnown {
			// New file: update job stage and location
			watcher.registry.UpdateJob(jobID, func(job *jobs.JobState) {
				job.Stage = stageName
				job.Location = locationName
				job.Artifact = filepath.Join(directoryPath, filename)
			})
		}
	}

	// Check for deleted files (cleanup stale lastSeen entries)
	for filename := range watcher.lastSeen {
		if !currentFiles[filename] {
			delete(watcher.lastSeen, filename)
		}
	}

	return nil
}

// extractJobID extracts the job ID from a filename.
// For now, we assume filenames are like "jobid_data.json" or "jobid.heightmap"
// This is a simple heuristic; adjust based on your naming scheme.
func extractJobID(filename string) string {
	// Remove extension
	base := strings.TrimSuffix(filename, filepath.Ext(filename))

	// If there's an underscore, take the part before it
	if underscoreIndex := strings.Index(base, "_"); underscoreIndex != -1 {
		return base[:underscoreIndex]
	}

	// Otherwise, the whole name is the job ID
	return base
}

// WatchLoop runs the watcher in a loop, polling at regular intervals.
func (watcher *Watcher) WatchLoop(interval time.Duration, stopChannel <-chan struct{}) {
	// Polling is intentionally simple to avoid external dependencies.
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-stopChannel:
			return
		case <-ticker.C:
			if err := watcher.Poll(); err != nil {
				fmt.Printf("poll error: %v\n", err)
			}
		}
	}
}
