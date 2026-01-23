package logs

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// Tailer reads logs from the MapGenerator logs/jobs/{jobID}/ folder structure.
// It dynamically reads all files in the job directory.
type Tailer struct {
	logsRoot  string // Path to logs/jobs directory
	mutexLock sync.RWMutex
	cache     map[string]LogData // jobID -> cached log data
}

// LogData holds all available logs for a job, mapped by filename.
type LogData struct {
	Files      map[string]string `json:"files"`
	LatestLine string            `json:"latest_line,omitempty"` // Derived status line
}

// NewTailer creates a new log tailer pointing to the logs/jobs directory.
func NewTailer(logsRoot string) *Tailer {
	return &Tailer{
		logsRoot:  logsRoot,
		mutexLock: sync.RWMutex{},
		cache:     make(map[string]LogData),
	}
}

// Tail reads all log files for a given jobID and returns the most recent log line.
func (tailer *Tailer) Tail(jobID string) string {
	tailer.mutexLock.Lock()
	defer tailer.mutexLock.Unlock()

	data := LogData{
		Files: make(map[string]string),
	}

	jobDir := filepath.Join(tailer.logsRoot, jobID)
	entries, err := os.ReadDir(jobDir)
	if err != nil {
		// Job directory might not exist yet
		return "(job directory not found)"
	}

	var newestModTime int64
	var bestLine string

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		info, err := entry.Info()
		if err != nil {
			continue
		}

		content := tailer.readLogFile(filepath.Join(jobDir, entry.Name()))
		if content != "" {
			data.Files[entry.Name()] = content
			
			// Track the most recently modified file to use its log as the status
			// We use ModTime to guess which stage was most recently active
			if info.ModTime().UnixNano() >= newestModTime {
				newestModTime = info.ModTime().UnixNano()
				bestLine = content
			}
		}
	}

	data.LatestLine = bestLine
	tailer.cache[jobID] = data

	if bestLine != "" {
		return bestLine
	}
	return "(no log entries yet)"
}

// readLogFile reads the last line from a log file.
// For JSONL files, parses the JSON; for plain text, returns the line as-is.
func (tailer *Tailer) readLogFile(filePath string) string {
	file, err := os.Open(filePath)
	if err != nil {
		return ""
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	var lastLine string

	for scanner.Scan() {
		lastLine = scanner.Text()
	}

	if lastLine == "" {
		return ""
	}

	// Try to parse as JSON for JSONL files
	if strings.HasSuffix(filePath, ".jsonl") || strings.HasSuffix(filePath, ".json") {
		var jsonObject map[string]interface{}
		if err := json.Unmarshal([]byte(lastLine), &jsonObject); err == nil {
			if message, exists := jsonObject["message"].(string); exists {
				return message
			}
			if message, exists := jsonObject["msg"].(string); exists {
				return message
			}
			return lastLine
		}
	}

	return lastLine
}

// GetLogsForJob returns all logs for a job as a structured object.
func (tailer *Tailer) GetLogsForJob(jobID string) LogData {
	tailer.mutexLock.RLock()
	if cached, exists := tailer.cache[jobID]; exists {
		tailer.mutexLock.RUnlock()
		return cached
	}
	tailer.mutexLock.RUnlock()

	// Not cached; read from disk (this also populates cache)
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
		if data.LatestLine != "" {
			return data.LatestLine
		}
	}
	return "(no log entries)"
}
