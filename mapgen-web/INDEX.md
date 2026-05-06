# 📚 MapGenerator Control Panel - Documentation Index

## Quick Links

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[DELIVERY.md](DELIVERY.md)** | 📦 What was built, features, testing | 5 min |
| **[README.md](README.md)** | 🔌 API endpoints, configuration, running | 5 min |
| **[DESIGN.md](DESIGN.md)** | 🏗️ Architecture decisions, why this way | 10 min |
| **[OVERVIEW.md](OVERVIEW.md)** | 📊 Visual diagrams, data flows, interactions | 10 min |
| **[IMPLEMENTATION.md](IMPLEMENTATION.md)** | ✅ Feature summary, code structure | 5 min |
| **[QUICKSTART.sh](QUICKSTART.sh)** | ⚡ Copy-paste commands | 2 min |

---

## Start Here

### If you want to...

**Get it running quickly:**
1. Read: [QUICKSTART.sh](QUICKSTART.sh)
2. Run: `go build -o bin/server ./cmd/server && ./bin/server`
3. Visit: `http://localhost:5003`

**Understand what it does:**
1. Read: [DELIVERY.md](DELIVERY.md) (5 min)
2. Look at: [OVERVIEW.md](OVERVIEW.md) (diagrams)

**Understand how it works:**
1. Read: [DESIGN.md](DESIGN.md) (decisions)
2. Read: [README.md](README.md) (API)
3. Browse: [cmd/server/main.go](cmd/server/main.go) (entry point)

**Extend or modify it:**
1. Read: [DESIGN.md](DESIGN.md) (philosophy)
2. Read: [cmd/server/main.go](cmd/server/main.go) (main logic)
3. Read: [internal/*/](internal) (specific packages)

---

## Code Structure

```
mapgen-web/
├── cmd/server/main.go
│   └─ HTTP handlers, job orchestration (280 lines)
│
├── internal/
│   ├─ jobs/registry.go       (85 lines) - Job state storage
│   ├─ pipeline/detector.go   (95 lines) - HeightmapAPI client
│   ├─ fswatch/watcher.go     (140 lines) - Directory polling
│   ├─ logs/tail.go           (65 lines) - Log extraction
│   └─ events/hub.go          (90 lines) - Event pub/sub
│
├─ web/index.html
│   └─ Browser dashboard (200 lines)
│
└─ Documentation (1,500+ lines)
```

---

## Key Concepts

### Job Lifecycle
```
START
  ↓
Heightmap/inbox  →  Heightmap/outbox
  ↓
Tiler/inbox  →  Tiler/outbox
  ↓
Weather/inbox  →  Weather/outbox
  ↓
TreePlanter/inbox  →  TreePlanter/outbox
  ↓
COMPLETE
```

### Information Flow
```
Browser → POST /api/jobs/start → HeightmapAPI → File appears in inbox
                                                      ↓
Browser ← GET /events ← Event Hub ← Filesystem Watcher ← File moves to outbox
          (SSE)                         (1s poll)
```

### Packages & Responsibilities
- **jobs**: Thread-safe in-memory registry
- **pipeline**: HTTP calls to external API
- **fswatch**: Poll directories, detect changes
- **logs**: Read file, grep by job ID
- **events**: Pub/sub for SSE broadcast

---

## API Reference

### POST /api/jobs/start
Start a new heightmap job
```bash
curl -X POST http://localhost:5003/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512}'
```

### GET /api/jobs
List all known jobs
```bash
curl http://localhost:5003/api/jobs | jq .
```

### GET /events
Server-Sent Events stream
```bash
curl -N http://localhost:5003/events
```

### GET /
HTML dashboard
```bash
curl http://localhost:5003/
```

---

## Configuration

**File:** `cmd/server/main.go` (lines ~25-30)
```go
httpPort := ":5003"                                    // Change this
heightmapAPIURL := "http://localhost:8000"             // Change this
logPath := os.ExpandEnv("$HOME/Code/...")              // Change this
```

---

## Dependencies

**None!** Standard Go library only.

**Requires:**
- Go 1.21+
- MapGenerator pipeline directories
- HeightmapAPI running
- `minicli.log` file (optional, for log lines)

---

## Testing

### Manual Test Sequence
```bash
# 1. Start server
go run ./cmd/server

# 2. In another terminal, check jobs (should be empty)
curl http://localhost:5003/api/jobs

# 3. Start a job
curl -X POST http://localhost:5003/api/jobs/start \
  -d '{"width": 512, "height": 512}' \
  -H 'Content-Type: application/json'

# 4. List jobs (should show one)
curl http://localhost:5003/api/jobs | jq .

# 5. Stream events (in third terminal)
curl -N http://localhost:5003/events

# 6. Open browser
open http://localhost:5003

# 7. Create some files in inbox to simulate pipeline
touch ~/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/inbox/jobid_data.json

# 8. Watch browser update in real-time
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5003 in use | Change `httpPort := ":5004"` in main.go |
| HeightmapAPI not found | Check URL in main.go, ensure API is running |
| Log file missing | Create empty file or disable log tailer |
| No updates in browser | Check `/events` is streaming, check browser DevTools |
| Jobs not tracking | Check directories exist: `ls ~/Code/.../Heightmap/inbox` |

---

## Performance Notes

- **Polling interval:** 1 second (can be adjusted)
- **Log tailer interval:** 2 seconds (can be adjusted)
- **Memory per job:** ~500 bytes
- **SSE buffer:** 10 events per client
- **Port:** 5003

---

## Future Ideas

- [ ] Switch to inotify/fsnotify for efficiency
- [ ] Add job history (SQLite)
- [ ] Add job control (restart, retry)
- [ ] Support multiple pipelines
- [ ] Add metrics endpoint
- [ ] Docker container
- [ ] Systemd service
- [ ] Web UI improvements (charts, filtering)

---

## File Manifest

### Source Code
- `cmd/server/main.go` - Entry point
- `internal/jobs/registry.go` - State storage
- `internal/pipeline/detector.go` - API client
- `internal/fswatch/watcher.go` - Polling watcher
- `internal/logs/tail.go` - Log extractor
- `internal/events/hub.go` - Event hub
- `web/index.html` - Frontend
- `go.mod` - Module manifest

### Documentation
- `README.md` - Usage & API
- `DESIGN.md` - Architecture
- `OVERVIEW.md` - Visuals & flows
- `DELIVERY.md` - Summary
- `IMPLEMENTATION.md` - Features
- `QUICKSTART.sh` - Commands
- `INDEX.md` - This file

---

## Getting Started (3 Steps)

```bash
# Step 1: Build
cd ~/Code/RTSColonyTerrainGenerator/mapgen-web
go build -o bin/server ./cmd/server

# Step 2: Run
./bin/server

# Step 3: Visit
open http://localhost:5003
```

---

## Questions?

Refer to the appropriate doc:
- **"How do I...?"** → [README.md](README.md)
- **"Why was...?"** → [DESIGN.md](DESIGN.md)
- **"What does...?"** → [OVERVIEW.md](OVERVIEW.md)
- **"What's included?"** → [DELIVERY.md](DELIVERY.md)
- **"Show me code..."** → Browse [internal/](internal)

---

**Last Updated:** January 20, 2026  
**Status:** ✅ Complete & Ready
