package logs

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// Tailer reads logs from a single aggregated log file.
type Tailer struct {
	logFilePath string
	mutexLock   sync.RWMutex
	cache       map[string]LogData // jobID -> cached log data
}

// LogData holds log information for a job.
// For the single-file approach, we just map "mapgen.log" to the latest line.
type LogData struct {
	Files      map[string]string `json:"files"`
	LatestLine string            `json:"latest_line,omitempty"`
}

// NewTailer creates a new log tailer pointing to the single mapgen.log file.
func NewTailer(logFilePath string) *Tailer {
	return &Tailer{
		logFilePath: logFilePath,
		mutexLock:   sync.RWMutex{},
		cache:       make(map[string]LogData),
	}
}

// Tail scans the single log file for lines containing the jobID and returns the most recent one.
// It also updates the cache.
func (tailer *Tailer) Tail(jobID string) string {
	tailer.mutexLock.Lock()
	defer tailer.mutexLock.Unlock()

	// Initialize empty data structure
	data := LogData{
		Files: make(map[string]string),
	}

	absPath, _ := filepath.Abs(tailer.logFilePath)
	// fmt.Printf("DEBUG: Tailing file: %s for JobID: %s\n", absPath, jobID)

	file, err := os.Open(tailer.logFilePath)
	if err != nil {
		fmt.Printf("ERROR: Could not open config log file: %s (Abs: %s) Error: %v\n", tailer.logFilePath, absPath, err)
		return "(log file not found)"
	}
	defer file.Close()

	var lastMatchingLine string
	scanner := bufio.NewScanner(file)

	// Allow for long log lines (payloads can be large).
	// Default max token is 64K which can truncate scans silently.
	const maxLogLineSize = 10 * 1024 * 1024
	scanner.Buffer(make([]byte, 1024), maxLogLineSize)

	// Simple linear scan of the entire file.
	// specific "grep" logic: checks if line contains jobID.
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, jobID) {
			lastMatchingLine = line
		}
	}

	// fmt.Printf("DEBUG: Scanned %d lines, found %d matches for %s\n", lineCount, matchCount, jobID)

	if err := scanner.Err(); err != nil {
		fmt.Printf("ERROR: Scanner error on file %s: %v\n", absPath, err)
		if lastMatchingLine == "" {
			data.LatestLine = "(log scan error)"
			data.Files["mapgen.log"] = "(log scan error)"
			tailer.cache[jobID] = data
			return data.LatestLine
		}
	}

	if lastMatchingLine != "" {
		data.LatestLine = lastMatchingLine
		data.Files["mapgen.log"] = lastMatchingLine // Present the line as if it's the file content for now
	} else {
		data.LatestLine = "(no log entries for this job)"
	}

	tailer.cache[jobID] = data
	return data.LatestLine
}

// GetLogsForJob returns the cached logs.
// It triggers a fresh Tail if not found, but typically the periodic loop will keep this warm.
func (tailer *Tailer) GetLogsForJob(jobID string) LogData {
	tailer.mutexLock.RLock()
	// Check cache first
	if cached, exists := tailer.cache[jobID]; exists {
		tailer.mutexLock.RUnlock()
		return cached
	}
	tailer.mutexLock.RUnlock()

	// Force a read if not in cache
	tailer.Tail(jobID)

	tailer.mutexLock.RLock()
	defer tailer.mutexLock.RUnlock()
	return tailer.cache[jobID]
}

// GetLine returns the last known log line for a job (from cache).
func (tailer *Tailer) GetLine(jobID string) string {
	tailer.mutexLock.RLock()
	defer tailer.mutexLock.RUnlock()

	if data, exists := tailer.cache[jobID]; exists {
		return data.LatestLine
	}
	return ""
}
