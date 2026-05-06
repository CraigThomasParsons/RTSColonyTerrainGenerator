package pipeline

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// HeightmapAPIClient issues HTTP requests to the Heightmap API for enqueueing
// jobs. It is intentionally minimal, uses only the standard library, and mirrors
// the PHP enqueue endpoint semantics documented in the Heightmap API.
type HeightmapAPIClient struct {
	baseURL string
}

// EnqueueRequest is the JSON payload sent to the Heightmap API.
type EnqueueRequest struct {
	Width  int `json:"width"`
	Height int `json:"height"`
}

// EnqueueResponse is the JSON response from the Heightmap API.
type EnqueueResponse struct {
	OK      bool   `json:"ok"`
	JobID   string `json:"job_id"`
	JobFile string `json:"job_file"`
	Error   string `json:"error,omitempty"`
}

// NewHeightmapAPIClient creates a new client for the Heightmap API.
// baseURL should be something like "http://localhost:8000"
func NewHeightmapAPIClient(baseURL string) *HeightmapAPIClient {
	// Trim any trailing slash so path joins remain predictable.
	return &HeightmapAPIClient{
		baseURL: strings.TrimSuffix(baseURL, "/"),
	}
}

// EnqueueJob sends a job to the Heightmap API.
// It returns the job_id and filename if successful.
func (client *HeightmapAPIClient) EnqueueJob(width, height int) (jobID, filename string, err error) {
	requestURL := client.baseURL + "/enqueue"

	requestPayload := EnqueueRequest{
		Width:  width,
		Height: height,
	}

	serializedPayload, marshalError := json.Marshal(requestPayload)
	if marshalError != nil {
		return "", "", fmt.Errorf("failed to marshal request: %w", marshalError)
	}

	// Build HTTP request explicitly so headers are easy to audit.
	httpRequest, requestCreationError := http.NewRequest("POST", requestURL, strings.NewReader(string(serializedPayload)))
	if requestCreationError != nil {
		return "", "", fmt.Errorf("failed to create request: %w", requestCreationError)
	}

	httpRequest.Header.Set("Content-Type", "application/json")

	// Use a bounded timeout to avoid hanging callers.
	httpClient := &http.Client{
		Timeout: 10 * time.Second,
	}

	httpResponse, callError := httpClient.Do(httpRequest)
	if callError != nil {
		return "", "", fmt.Errorf("failed to call HeightmapAPI: %w", callError)
	}
	defer httpResponse.Body.Close()

	responseBody, readError := io.ReadAll(httpResponse.Body)
	if readError != nil {
		return "", "", fmt.Errorf("failed to read response: %w", readError)
	}

	var apiResponse EnqueueResponse
	if unmarshalError := json.Unmarshal(responseBody, &apiResponse); unmarshalError != nil {
		return "", "", fmt.Errorf("failed to unmarshal response: %w", unmarshalError)
	}

	// Propagate API-declared errors with context.
	if !apiResponse.OK {
		return "", "", fmt.Errorf("API error: %s", apiResponse.Error)
	}

	if apiResponse.JobID == "" || apiResponse.JobFile == "" {
		return "", "", fmt.Errorf("API response missing job_id or job_file")
	}

	return apiResponse.JobID, apiResponse.JobFile, nil
}
