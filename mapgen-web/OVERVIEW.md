# MapGenerator Control Plane - Project Structure & Overview

## File Tree

```
mapgen-web/
│
├── cmd/server/
│   └── main.go                    # 🚀 Entry point, HTTP server, handlers (~280 lines)
│
├── internal/
│   ├── jobs/
│   │   └── registry.go            # 💾 Thread-safe in-memory job store (~85 lines)
│   │
│   ├── pipeline/
│   │   └── detector.go            # 🔗 HTTP client for HeightmapAPI (~95 lines)
│   │
│   ├── fswatch/
│   │   └── watcher.go             # 👀 Poll pipeline directories (~140 lines)
│   │
│   ├── logs/
│   │   └── tail.go                # 📝 Extract log lines by job ID (~65 lines)
│   │
│   └── events/
│       └── hub.go                 # 📢 Pub/sub event broadcasting (~90 lines)
│
├── web/
│   └── index.html                 # 🎨 Browser dashboard with SSE client (~200 lines)
│
├── go.mod                         # Module manifest
├── README.md                       # API docs & usage guide
├── DESIGN.md                       # Architecture & design decisions
├── IMPLEMENTATION.md               # Complete feature summary
└── QUICKSTART.sh                   # Quick reference commands

Total: ~1,000 lines of Go + HTML
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Browser Client                              │
│  (index.html)                                                    │
│  ┌──────────────────────┐      ┌──────────────────────┐         │
│  │ Start New Job Form   │      │ SSE Event Stream     │         │
│  │ (width, height)      │      │ (live updates)       │         │
│  └──────────────────────┘      └──────────────────────┘         │
│           │                              │                       │
│           └──────────────┬───────────────┘                       │
│                          ↓                                       │
└─────────────────────────────────────────────────────────────────┘
                           │
              POST /api/jobs/start
              GET /events (SSE)
                           │
                           ↓
     ┌─────────────────────────────────────────────────┐
     │           HTTP Server (port 5003)               │
     │ (cmd/server/main.go)                            │
     ├─────────────────────────────────────────────────┤
     │                                                 │
     │  ┌─────────────────────────────────────────┐   │
     │  │ handleStartJob()                        │   │
     │  │ 1. Validate input (width, height)       │   │
     │  │ 2. Call HeightmapAPI.EnqueueJob()       │   │
     │  │ 3. registry.RegisterJob(jobID)          │   │
     │  │ 4. hub.PublishJobUpdate()               │   │
     │  │ 5. Return 201 + jobID                   │   │
     │  └─────────────────────────────────────────┘   │
     │                                                 │
     │  ┌─────────────────────────────────────────┐   │
     │  │ handleEvents()                          │   │
     │  │ 1. Subscribe to hub                     │   │
     │  │ 2. Stream events as SSE                 │   │
     │  │ 3. Flush after each event               │   │
     │  │ 4. Unsubscribe on disconnect            │   │
     │  └─────────────────────────────────────────┘   │
     │                                                 │
     └─────────────────────────────────────────────────┘
                           │
                ┌──────────┼──────────┐
                ↓          ↓          ↓
        ┌──────────┐  ┌────────┐  ┌──────────┐
        │ Registry │  │  Hub   │  │ Watcher  │
        │          │  │        │  │          │
        │ jobs map │  │channel │  │ polling  │
        │ (RAM)    │  │ map    │  │ loop     │
        └──────────┘  └────────┘  └──────────┘
             │            ▲           │
             │            │           │
             │     UpdateJob()        Poll()
             │            │           │
             │            └───────────┘
             │                    │
             └────────────────────┼─────────────────────────────┐
                                  │                             │
                                  ↓                             ↓
                    ┌──────────────────────┐    ┌──────────────────────┐
                    │   Filesystem Watch   │    │   Log Tailer         │
                    │                      │    │                      │
                    │ Every 1 second:      │    │ Every 2 seconds:     │
                    │ 1. Poll 8 dirs       │    │ 1. Read log file     │
                    │ 2. Detect stage      │    │ 2. Grep by jobID     │
                    │ 3. Detect location   │    │ 3. Store last line   │
                    │ 4. Update job state  │    │ 4. Cache result      │
                    │ 5. Publish update    │    │ 5. Publish via hub   │
                    └──────────────────────┘    └──────────────────────┘
                                  │                             │
                                  └─────────────────┬───────────┘
                                                    ↓
                    ┌──────────────────────────────────────────────┐
                    │        MapGenerator Pipeline                 │
                    ├──────────────────────────────────────────────┤
                    │                                              │
                    │  Heightmap/     Tiler/        Weather/       │
                    │  inbox→outbox   inbox→outbox  inbox→outbox  │
                    │                                              │
                    │  TreePlanter/                                │
                    │  inbox→outbox                                │
                    │                                              │
                    └──────────────────────────────────────────────┘
                                    │
                                    ↓
                    ┌──────────────────────────────────────────────┐
                    │      HeightmapAPI (external)                 │
                    │      POST /enqueue                           │
                    │      ← {job_id, job_file}                    │
                    └──────────────────────────────────────────────┘
```

---

## Key Interactions

### 1. Start Job
```
Browser → POST /api/jobs/start {width, height}
          ↓
          handleStartJob()
          ├→ client.EnqueueJob(width, height)
          │   ├→ POST http://localhost:8000/enqueue
          │   └→ {ok: true, job_id: "abc123", job_file: "..."}
          ├→ registry.RegisterJob(jobID, filename)
          │   └→ Create JobState in memory
          ├→ hub.PublishJobUpdate(job)
          │   └→ Broadcast to all SSE subscribers
          └→ 201 Created {job_id, filename}
          ↓
Browser → Receives response, displays in table
```

### 2. Track Progress (Background Loop)
```
Every 1 second:
  watcher.Poll()
  ├→ Scan Heightmap/inbox/  → detect "heightmap" stage, "inbox" location
  ├→ Scan Heightmap/outbox/ → detect "heightmap" stage, "outbox" location
  ├→ Scan Tiler/inbox/      → detect "tiler" stage, "inbox" location
  ├→ Scan Tiler/outbox/     → detect "tiler" stage, "outbox" location
  └→ ... same for weather and treeplanter
  
  For each file found:
    registry.UpdateJob(jobID, func(job) {
      job.Stage = stage
      job.Location = location
      job.Artifact = path
    })
    hub.PublishJobUpdate(job)  → broadcast to SSE subscribers

Every 2 seconds:
  for each job in registry:
    logLine := tailer.Tail(jobID)
    registry.UpdateJob(jobID, func(job) {
      job.LastLogLine = logLine
    })
    hub.PublishJobUpdate(job)  → broadcast to SSE subscribers
```

### 3. Stream Updates to Browser
```
Browser → GET /events
          ↓
          handleEvents()
          └→ ch := hub.Subscribe()
             Loop:
               event := ← ch
               io.WriteString(w, event.FormatSSE())
               flusher.Flush()
          ↓
Browser → Receives SSE data:
          {
            "type": "job_updated",
            "data": {
              "job_id": "abc123",
              "stage": "heightmap",
              "location": "outbox",
              "last_log_line": "[12:34] Done",
              "updated_at": "2026-01-20T12:34:56Z"
            },
            "timestamp": "2026-01-20T12:34:56Z"
          }
          ↓
          JavaScript parses JSON, updates table
```

---

## State Transitions

A single job flows through states as it progresses:

```
START JOB
  ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage: heightmap                                           │
│  Location: inbox     (waiting to be processed)              │
│  Artifact: (none yet)                                       │
└─────────────────────────────────────────────────────────────┘
  ↓ (HeightmapAPI process picks up file)
┌─────────────────────────────────────────────────────────────┐
│  Stage: heightmap                                           │
│  Location: outbox    (processed by heightmap service)       │
│  Artifact: Heightmap/outbox/abc123_data.heightmap           │
│  LastLogLine: "[12:34] Heightmap generated"                 │
└─────────────────────────────────────────────────────────────┘
  ↓ (Tiler picks up heightmap file)
┌─────────────────────────────────────────────────────────────┐
│  Stage: tiler                                               │
│  Location: outbox    (processed by tiler service)           │
│  Artifact: Tiler/outbox/abc123_tiles.zip                    │
│  LastLogLine: "[12:45] Tiler complete"                      │
└─────────────────────────────────────────────────────────────┘
  ↓ (WeatherAnalyses picks up)
┌─────────────────────────────────────────────────────────────┐
│  Stage: weather                                             │
│  Location: outbox                                           │
│  Artifact: WeatherAnalyses/outbox/abc123_weather.json       │
│  LastLogLine: "[13:00] Weather data ready"                  │
└─────────────────────────────────────────────────────────────┘
  ↓ (TreePlanter picks up)
┌─────────────────────────────────────────────────────────────┐
│  Stage: treeplanter                                         │
│  Location: outbox    (final output)                         │
│  Artifact: TreePlanter/outbox/abc123_world.zip              │
│  LastLogLine: "[13:30] Pipeline complete"                   │
└─────────────────────────────────────────────────────────────┘
DONE
```

---

## Component Responsibilities

| Package | Responsibility | Test By |
|---------|-----------------|---------|
| `jobs/registry` | Store job state in memory with RW locks | `ListJobs()` should return all registered jobs |
| `pipeline/detector` | Call HeightmapAPI and parse response | `curl http://localhost:8000/enqueue` should work |
| `fswatch/watcher` | Poll directories and detect file locations | `ls ~/Code/RTSColonyTerrainGenerator/MapGenerator/*/inbox` |
| `logs/tail` | Read log file and extract job-relevant lines | `grep jobid minicli.log` should show lines |
| `events/hub` | Broadcast updates to all SSE subscribers | `curl -N http://localhost:5003/events` should stream |
| `cmd/server` | Route HTTP requests to handlers | `curl http://localhost:5003/api/jobs` should work |
| `web/index.html` | Display dashboard and trigger jobs | Open `http://localhost:5003` in browser |

---

## Testing Checklist

- [ ] Go installed (`go version`)
- [ ] Build succeeds (`go build -o bin/server ./cmd/server`)
- [ ] Server starts (`./bin/server`)
- [ ] `/api/jobs` returns `[]` initially (`curl http://localhost:5003/api/jobs`)
- [ ] `/` serves HTML (`curl http://localhost:5003/`)
- [ ] HeightmapAPI is running (`curl http://localhost:8000/...`)
- [ ] Can trigger job (`curl -X POST http://localhost:5003/api/jobs/start ...`)
- [ ] Job appears in registry (`curl http://localhost:5003/api/jobs | jq`)
- [ ] SSE streams events (`curl -N http://localhost:5003/events`)
- [ ] Browser shows dashboard (`open http://localhost:5003`)
- [ ] Browser shows live updates via SSE

---

## Quick Debugging

**Server won't start?**
```bash
lsof -i :5003  # Check if port is in use
go run ./cmd/server  # Run with output
```

**Jobs not being detected?**
```bash
ls ~/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/inbox/
# If empty, HeightmapAPI job creation failed
curl -X POST http://localhost:8000/enqueue -d '{"width":512,"height":512}' -H 'Content-Type: application/json'
```

**SSE not streaming?**
```bash
curl -N http://localhost:5003/events
# Trigger job in another terminal, watch for updates
```

**Log lines not appearing?**
```bash
tail -f ~/Code/RTSColonyTerrainGenerator/MapGenerator/minicli.log
# Start a job, look for lines with job ID
```

---

## Deploy Checklist

- [ ] Go 1.21+ installed
- [ ] All pipeline directories exist and are writable
- [ ] HeightmapAPI running on expected URL
- [ ] minicli.log exists and is readable
- [ ] Port 5003 is available
- [ ] Build: `go build -o bin/server ./cmd/server`
- [ ] Run: `./bin/server`
- [ ] Test endpoints (see checklist above)
- [ ] Browser dashboard accessible at `http://localhost:5003`

---

**Status:** ✅ Complete and ready for testing
