package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"mapgen-web/internal/events"
	"mapgen-web/internal/fswatch"
	"mapgen-web/internal/jobs"
	"mapgen-web/internal/logs"
	"mapgen-web/internal/pipeline"
)

// Server bundles all control-plane dependencies for the MapGenerator pipeline.
// It owns the registry, filesystem watcher, SSE hub, log tailer, and API client.
type Server struct {
	registry  *jobs.Registry
	eventHub  *events.Hub
	watcher   *fswatch.Watcher
	logTailer *logs.Tailer
	apiClient *pipeline.HeightmapAPIClient
	mutexLock sync.RWMutex
}

// StartJobRequest is the JSON payload for POST /api/jobs/start
type StartJobRequest struct {
	Width  int `json:"width"`
	Height int `json:"height"`
}

// StartJobResponse is the JSON response from POST /api/jobs/start
type StartJobResponse struct {
	JobID    string `json:"job_id,omitempty"`
	Filename string `json:"filename,omitempty"`
	Error    string `json:"error,omitempty"`
}

func main() {
	// Configuration (read from environment or use defaults)
	httpPort := ":5003" // Run on port 5003 to avoid conflicts
	heightmapAPIURL := os.Getenv("HEIGHTMAP_API_URL")
	if heightmapAPIURL == "" {
		heightmapAPIURL = "http://localhost:8099" // Default for local development
	}

	// Path to logs/jobs directory (where job logs are organized by jobID)
	logsJobsPath := os.Getenv("LOGS_JOBS_PATH")
	if logsJobsPath == "" {
		// Default to local logs/jobs when running outside Docker
		logsJobsPath = "./logs/jobs"
	}

	// Create server components
	registry := jobs.NewRegistry()
	eventHub := events.NewHub()
	watcher := fswatch.NewWatcher(registry)
	logTailer := logs.NewTailer(logsJobsPath)
	heightmapClient := pipeline.NewHeightmapAPIClient(heightmapAPIURL)

	server := &Server{
		registry:  registry,
		eventHub:  eventHub,
		watcher:   watcher,
		logTailer: logTailer,
		apiClient: heightmapClient,
	}

	// Start the filesystem watcher in the background
	stopChannel := make(chan struct{})
	go watcher.WatchLoop(1*time.Second, stopChannel)

	// Start the log tailer in the background (updates log lines periodically)
	go server.updateLogsLoop(stopChannel)

	// Register HTTP handlers
	http.HandleFunc("/", server.handleRoot)
	http.HandleFunc("/events", server.handleEvents)
	http.HandleFunc("/api/jobs/start", server.handleStartJob)
	http.HandleFunc("/api/jobs", server.handleListJobs)
	http.HandleFunc("/api/jobs/logs/", server.handleGetJobLogs)

	log.Printf("🚀 MapGenerator Control Plane starting on %s", httpPort)
	log.Printf("   HeightmapAPI: %s", heightmapAPIURL)
	log.Printf("   Logs path: %s", logsJobsPath)

	if listenError := http.ListenAndServe(httpPort, nil); listenError != nil {
		log.Fatalf("server error: %v", listenError)
	}
}

// handleRoot serves the static HTML dashboard.
func (server *Server) handleRoot(responseWriter http.ResponseWriter, request *http.Request) {
	if request.URL.Path != "/" {
		http.NotFound(responseWriter, request)
		return
	}

	responseWriter.Header().Set("Content-Type", "text/html")
	http.ServeFile(responseWriter, request, "web/index.html")
}

// handleStartJob handles POST /api/jobs/start to enqueue a new heightmap job.
func (server *Server) handleStartJob(responseWriter http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodPost {
		http.Error(responseWriter, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse request
	var startJobRequest StartJobRequest
	if decodeError := json.NewDecoder(request.Body).Decode(&startJobRequest); decodeError != nil {
		responseWriter.Header().Set("Content-Type", "application/json")
		responseWriter.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(responseWriter).Encode(StartJobResponse{
			Error: fmt.Sprintf("invalid request: %v", decodeError),
		})
		return
	}

	// Validate input
	if startJobRequest.Width <= 0 || startJobRequest.Height <= 0 {
		responseWriter.Header().Set("Content-Type", "application/json")
		responseWriter.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(responseWriter).Encode(StartJobResponse{
			Error: "width and height must be positive integers",
		})
		return
	}

	log.Printf("📝 Enqueueing heightmap job: %dx%d", startJobRequest.Width, startJobRequest.Height)

	// Call the HeightmapAPI to enqueue the job
	jobID, filename, enqueueError := server.apiClient.EnqueueJob(startJobRequest.Width, startJobRequest.Height)
	if enqueueError != nil {
		log.Printf("❌ Failed to enqueue job: %v", enqueueError)
		responseWriter.Header().Set("Content-Type", "application/json")
		responseWriter.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(responseWriter).Encode(StartJobResponse{
			Error: fmt.Sprintf("failed to enqueue: %v", enqueueError),
		})
		return
	}

	// Register the job locally
	job := server.registry.RegisterJob(jobID, filename)
	log.Printf("✅ Job registered: %s (%s)", jobID, filename)

	// Broadcast the job to all connected clients
	server.eventHub.PublishJobUpdate(job)

	// Return success
	responseWriter.Header().Set("Content-Type", "application/json")
	responseWriter.WriteHeader(http.StatusCreated)
	json.NewEncoder(responseWriter).Encode(StartJobResponse{
		JobID:    jobID,
		Filename: filename,
	})
}

// handleListJobs handles GET /api/jobs to return all registered jobs.
func (server *Server) handleListJobs(responseWriter http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		http.Error(responseWriter, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	jobs := server.registry.ListJobs()
	responseWriter.Header().Set("Content-Type", "application/json")
	json.NewEncoder(responseWriter).Encode(jobs)
}

// handleGetJobLogs handles GET /api/jobs/logs/{jobID} to return detailed logs for a job.
func (server *Server) handleGetJobLogs(responseWriter http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		http.Error(responseWriter, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract jobID from path: /api/jobs/logs/{jobID}
	jobID := strings.TrimPrefix(request.URL.Path, "/api/jobs/logs/")
	if jobID == "" {
		responseWriter.Header().Set("Content-Type", "application/json")
		responseWriter.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(responseWriter).Encode(map[string]string{"error": "job_id required"})
		return
	}

	// Fetch detailed logs for this job
	logData := server.logTailer.GetLogsForJob(jobID)

	responseWriter.Header().Set("Content-Type", "application/json")
	json.NewEncoder(responseWriter).Encode(logData)
}

// handleEvents handles GET /events to stream job updates via SSE.
func (server *Server) handleEvents(responseWriter http.ResponseWriter, request *http.Request) {
	// Set up SSE headers
	responseWriter.Header().Set("Content-Type", "text/event-stream")
	responseWriter.Header().Set("Cache-Control", "no-cache")
	responseWriter.Header().Set("Connection", "keep-alive")
	responseWriter.Header().Set("Access-Control-Allow-Origin", "*")

	// Flush the headers immediately so the client starts receiving
	if flusher, isFlushCapable := responseWriter.(http.Flusher); isFlushCapable {
		flusher.Flush()
	}

	// Subscribe to the event hub
	eventChannel := server.eventHub.Subscribe()
	defer server.eventHub.Unsubscribe(eventChannel)

	// Stream events to the client
	for {
		select {
		case <-request.Context().Done():
			// Client disconnected
			return

		case event, channelOpen := <-eventChannel:
			if !channelOpen {
				return
			}

			// Write the event as SSE
			sseData := events.FormatSSE(event)
			if _, writeError := io.WriteString(responseWriter, sseData); writeError != nil {
				log.Printf("⚠️  SSE write error: %v", writeError)
				return
			}

			// Flush to send immediately
			if flusher, isFlushCapable := responseWriter.(http.Flusher); isFlushCapable {
				flusher.Flush()
			}
		}
	}
}

// updateLogsLoop periodically updates log lines for all known jobs.
// This runs in a background goroutine.
func (server *Server) updateLogsLoop(stopChannel <-chan struct{}) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-stopChannel:
			return

		case <-ticker.C:
			// Fetch all jobs and update their log lines
			allJobs := server.registry.ListJobs()
			for _, job := range allJobs {
				logLine := server.logTailer.Tail(job.JobID)
				server.registry.UpdateJob(job.JobID, func(jobState *jobs.JobState) {
					jobState.LastLogLine = logLine
				})
			}
		}
	}
}
