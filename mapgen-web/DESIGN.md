# Design Decisions & Architecture

## Why This Approach?

### 1. Filesystem as Source of Truth
**Decision:** All job state is derived from filesystem locations (inbox/outbox directories).

**Rationale:**
- MapGenerator already writes files to directories
- No need for a separate database
- Filesystem is always in sync with reality
- If server crashes, no state is lost
- Makes debugging trivial (ls the directories)

**Trade-off:** Polling instead of inotify (slower but simpler, good enough for now)

---

### 2. In-Memory Registry
**Decision:** Keep a local copy of job state in memory, updated by polling.

**Rationale:**
- Fast reads for HTTP responses
- Browser can request current state without filesystem stat calls
- Job metadata (log lines, timestamps) fit easily in RAM
- Serves as a cache between poll intervals

**Implementation:**
```go
type JobState struct {
    JobID       string    // From HeightmapAPI response
    Filename    string    // From HeightmapAPI response
    Stage       string    // Detected from directory location
    Location    string    // inbox | processing | outbox | failed
    Artifact    string    // Full path to file
    LastLogLine string    // Extracted from log file
    UpdatedAt   time.Time // When we last saw a change
}
```

---

### 3. Event Hub for Broadcasts
**Decision:** Pub/sub pattern with non-blocking sends to slow clients.

**Rationale:**
- Multiple browsers can connect simultaneously
- Updates should reach all clients in parallel
- Slow network clients shouldn't block others
- Simple to understand and debug

**Implementation:**
```go
// Non-blocking send: if channel full, skip subscriber
select {
case ch <- event:
default:
    // Channel buffer full, skip this subscriber
}
```

---

### 4. Filesystem Watching Strategy
**Decision:** Simple polling loop instead of inotify.

**Rationale:**
- Standard Go library only (no external deps)
- Simpler to understand and debug
- More portable (works on all systems)
- 1-second poll interval is acceptable for this use case
- Can upgrade to fsnotify later if needed

**Watched Directories:**
```
Heightmap/   {inbox, outbox}
Tiler/       {inbox, outbox}
Weather/     {inbox, outbox}
TreePlanter/ {inbox, outbox}
```

**Job ID Extraction:**
Assumes filenames like `jobid_data.json` or `jobid.heightmap`
```go
func extractJobID(filename string) string {
    base := strings.TrimSuffix(filename, filepath.Ext(filename))
    if idx := strings.Index(base, "_"); idx != -1 {
        return base[:idx]
    }
    return base
}
```

---

### 5. Log Tailing
**Decision:** Grep through entire log file every 2 seconds, extract lines with job ID.

**Rationale:**
- Simple and correct
- Log files are not that large (kilobytes)
- No need for fancy tail -f logic
- Easy to debug (just grep the log manually)
- Better than nothing; full solution would use real log parsing

**Cached Results:**
```go
t.lines[jobID] = lastLine  // Store result
```

---

### 6. HeightmapAPI Client
**Decision:** HTTP client with explicit error handling.

**Rationale:**
- Reflects reality: job starts with API call
- Validated contract: must check response is OK
- Timeout protection: 10-second timeout
- Clear request/response types

**Request Validation:**
```go
type EnqueueRequest struct {
    Width  int `json:"width"`
    Height int `json:"height"`
}
```

---

### 7. Server-Sent Events (SSE)
**Decision:** Use HTTP SSE instead of WebSocket.

**Rationale:**
- SSE is simpler (uses standard HTTP)
- Unidirectional stream (server→browser only)
- Auto-reconnect built-in
- No need for binary frames or framing logic
- Easier to debug with curl/browser DevTools

**Format:**
```
data: {"type":"job_updated","data":{...},"timestamp":"2026-01-20T12:34:56Z"}\n\n
```

---

### 8. Minimal Frontend
**Decision:** Vanilla HTML5 + vanilla JavaScript, no frameworks.

**Rationale:**
- Clarity is paramount
- No build step needed
- Can read and understand in 5 minutes
- No version conflicts or dependency hell
- Works in any browser

**Responsibilities:**
1. Connect to `/events` SSE stream
2. Parse JSON and update table
3. Show status (color-coded)
4. Log recent events
5. Form to start new jobs

---

### 9. Thread Safety
**Decision:** Mutex-protected registry, buffered channels for events.

**Implementation:**
```go
type Registry struct {
    mu   sync.RWMutex
    jobs map[string]*JobState
}

// All operations:
// - acquire lock before reading/writing jobs map
// - release immediately after (no long-held locks)
```

---

### 10. Error Handling
**Decision:** Graceful degradation; one failure doesn't break the whole system.

**Examples:**
- Missing directory: skip, continue polling other dirs
- HeightmapAPI unreachable: return 500 to client, don't crash
- Log file missing: return placeholder text "(log unavailable)"
- Slow filesystem: don't block watcher thread

---

## Why NOT...

### Not a Database
- Filesystem is already the DB
- Would add complexity with no benefit
- Job history isn't needed for MVP

### Not a Message Queue
- Not needed; filesystem is the queue
- Each stage has its own inbox/outbox
- No need for distributed state

### Not a Distributed System
- Single process is fine
- Can always shard later
- Simpler to debug now

### Not GraphQL/REST Schema Validation
- JSON is self-documenting
- Simple requests/responses
- No complex filtering needed

### Not Authentication
- Internal service only (implied)
- Can add later if exposed publicly
- Keeps focus on functionality

---

## Performance Characteristics

**Polling Overhead:**
- 8 directories × 1-second interval = `ls` calls every second
- ~10KB filesystem stat overhead
- Negligible compared to pipeline computation time

**Memory Usage:**
- ~500 bytes per job in registry
- Typical: 10-100 jobs active
- Total: <100KB in memory

**Network Overhead:**
- SSE uses HTTP keep-alive
- JSON events: ~500 bytes each
- Broadcast to all clients is O(n) where n=clients

**Log Tailing:**
- Read entire log file every 2 seconds
- Assume log <10MB: negligible
- grep by jobID is fast in Go

---

## Debugging Checklist

When something doesn't work:

1. **Check directories exist:**
   ```bash
   ls ~/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/inbox
   ```

2. **Watch files in real-time:**
   ```bash
   watch -n 0.5 'ls -la ~/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/inbox'
   ```

3. **Check HeightmapAPI is running:**
   ```bash
   curl http://localhost:8000/enqueue -d '{"width":512,"height":512}' -H 'Content-Type: application/json'
   ```

4. **Check log file exists and has data:**
   ```bash
   tail -f ~/Code/RTSColonyTerrainGenerator/MapGenerator/minicli.log
   ```

5. **Check server is running:**
   ```bash
   curl http://localhost:5003/api/jobs
   ```

6. **Check SSE is broadcasting:**
   ```bash
   curl -N http://localhost:5003/events
   ```

7. **Check browser console for errors:**
   - Open DevTools (F12)
   - Look for network errors or JavaScript errors
   - Check Console tab

---

## Future Improvements

If you need to enhance this:

### Phase 2: Efficiency
1. Replace polling with `fsnotify` library
2. Add metrics endpoint (jobs/sec, latency)
3. Compress log file periodically

### Phase 3: Control
1. Job cancellation endpoint
2. Job retry endpoint
3. Manual file movement (bypass normal flow)

### Phase 4: Persistence
1. SQLite for job history
2. Survive server restarts
3. Query by date range

### Phase 5: Integration
1. Systemd service file
2. Docker container
3. Config file (YAML) instead of hardcoded constants

---

**Key Principle:** Start simple, make it work, optimize only if needed.

This implementation prioritizes clarity and correctness over cleverness.
