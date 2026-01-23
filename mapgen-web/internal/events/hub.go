package events

import (
	"encoding/json"
	"fmt"
	"mapgen-web/internal/jobs"
	"sync"
)

// EventHub manages pub/sub for job state changes and broadcasts updates to
// all connected clients via SSE. The design favors availability over strict
// delivery guarantees; slow clients may drop events.
type Hub struct {
	mutexLock   sync.RWMutex
	subscribers map[chan *Event]bool
}

// Event represents a job state change to be sent to clients.
type Event struct {
	Type string         `json:"type"` // "job_updated"
	Data *jobs.JobState `json:"data"`
	Time string         `json:"timestamp"`
}

// NewHub creates a new event hub.
func NewHub() *Hub {
	return &Hub{
		subscribers: make(map[chan *Event]bool),
	}
}

// Subscribe registers a client channel for job updates.
func (hub *Hub) Subscribe() chan *Event {
	// Allocate a buffered channel so slow subscribers do not block publishers.
	hub.mutexLock.Lock()
	defer hub.mutexLock.Unlock()

	subscriberChannel := make(chan *Event, 10) // Buffered to avoid blocking
	hub.subscribers[subscriberChannel] = true
	return subscriberChannel
}

// Unsubscribe removes a client channel.
func (hub *Hub) Unsubscribe(subscriberChannel chan *Event) {
	hub.mutexLock.Lock()
	defer hub.mutexLock.Unlock()

	if _, exists := hub.subscribers[subscriberChannel]; exists {
		delete(hub.subscribers, subscriberChannel)
		close(subscriberChannel)
	}
}

// Publish broadcasts an event to all subscribers.
// It does not block on slow subscribers (will skip them if channel is full).
func (hub *Hub) Publish(event *Event) {
	// Broadcast in a non-blocking fashion to keep the publisher fast and avoid
	// a single slow subscriber back-pressuring the hub.
	hub.mutexLock.RLock()
	defer hub.mutexLock.RUnlock()

	for subscriberChannel := range hub.subscribers {
		select {
		case subscriberChannel <- event:
		default:
			// Channel buffer full; skip to keep the hub responsive.
		}
	}
}

// PublishJobUpdate sends a job state update to all subscribers.
func (hub *Hub) PublishJobUpdate(job *jobs.JobState) {
	event := &Event{
		Type: "job_updated",
		Data: job,
		Time: job.UpdatedAt.Format("2006-01-02T15:04:05Z07:00"),
	}
	hub.Publish(event)
}

// EventToJSON converts an event to JSON bytes for SSE.
func EventToJSON(event *Event) []byte {
	data, _ := json.Marshal(event)
	return data
}

// FormatSSE formats an event as Server-Sent Event data.
func FormatSSE(event *Event) string {
	jsonData := EventToJSON(event)
	return fmt.Sprintf("data: %s\n\n", string(jsonData))
}
