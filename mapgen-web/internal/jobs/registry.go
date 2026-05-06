package jobs

import (
	"sync"
	"time"
)

// JobState represents the state of a single job in the MapGenerator pipeline.
// This is the source of truth for job progress.
type JobState struct {
	JobID       string    `json:"job_id"`
	Filename    string    `json:"filename"`
	Stage       string    `json:"stage"`    // heightmap | tiler | weather | treeplanter
	Location    string    `json:"location"` // inbox | processing | outbox | failed
	Artifact    string    `json:"artifact"` // Path to the output file
	LastLogLine string    `json:"last_log_line"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// Registry maintains all job state in memory.
// All operations are thread-safe via mutex.
type Registry struct {
	mutexLock sync.RWMutex
	jobs      map[string]*JobState // key: JobID
}

// NewRegistry creates an empty job registry.
func NewRegistry() *Registry {
	return &Registry{
		jobs: make(map[string]*JobState),
	}
}

// RegisterJob creates a new job entry.
func (r *Registry) RegisterJob(jobID, filename string) *JobState {
	r.mutexLock.Lock()
	defer r.mutexLock.Unlock()

	job := &JobState{
		JobID:     jobID,
		Filename:  filename,
		Stage:     "heightmap",
		Location:  "inbox",
		UpdatedAt: time.Now(),
	}
	r.jobs[jobID] = job
	return job
}

// GetJob retrieves a job by ID.
func (r *Registry) GetJob(jobID string) *JobState {
	r.mutexLock.RLock()
	defer r.mutexLock.RUnlock()

	if job, exists := r.jobs[jobID]; exists {
		return job
	}
	return nil
}

// UpdateJob updates a job's state. Returns the updated job.
func (r *Registry) UpdateJob(jobID string, updateFunc func(*JobState)) *JobState {
	r.mutexLock.Lock()
	defer r.mutexLock.Unlock()

	if job, exists := r.jobs[jobID]; exists {
		updateFunc(job)
		job.UpdatedAt = time.Now()
		return job
	}
	return nil
}

// ListJobs returns a copy of all jobs.
func (r *Registry) ListJobs() []*JobState {
	r.mutexLock.RLock()
	defer r.mutexLock.RUnlock()

	jobs := make([]*JobState, 0, len(r.jobs))
	for _, job := range r.jobs {
		jobs = append(jobs, job)
	}
	return jobs
}

// JobExists checks if a job ID is registered.
func (r *Registry) JobExists(jobID string) bool {
	r.mutexLock.RLock()
	defer r.mutexLock.RUnlock()
	_, exists := r.jobs[jobID]
	return exists
}
