# MapGenerator Control Panel (Go)

A minimal HTTP control plane for the MapGenerator pipeline.  
Triggers jobs via HeightmapAPI, tracks progress via filesystem polling, and streams updates to browsers using Server-Sent Events (SSE).

## Architecture

**Filesystem-Driven Design:**
- Jobs are registered when sent to HeightmapAPI  
- Pipeline stages are monitored via polling (watch inbox/outbox directories)  
- Log lines are extracted by job ID  
- All state is in-memory; filesystem is source of truth  

**Components:**

| Package | Responsibility |
|---------|-----------------|
| `jobs/registry.go` | Thread-safe in-memory job state store |
| `pipeline/detector.go` | HTTP client for calling HeightmapAPI |
| `fswatch/watcher.go` | Polls pipeline directories, updates jobs |
| `logs/tail.go` | Extracts log lines by job ID |
| `events/hub.go` | Pub/sub for broadcasting job updates |
| `cmd/server/main.go` | HTTP server, handlers, orchestration |
| `web/index.html` | Minimal browser UI with SSE client |

## API Endpoints

```
GET  /               → Serve HTML dashboard
GET  /events         → Server-Sent Events stream
POST /api/jobs/start → Enqueue a heightmap job
GET  /api/jobs       → List all known jobs
```

### POST /api/jobs/start

**Request:**
```json
{ "width": 512, "height": 512 }
```

**Response (201 Created):**
```json
{ "job_id": "abc123xyz", "filename": "abc123xyz_data.json" }
```

**Behavior:**
1. Calls `http://localhost:8000/enqueue` (HeightmapAPI)  
2. Registers job locally with `stage=heightmap, location=inbox`  
3. Broadcasts update to all SSE clients  

### GET /events

Stream of Server-Sent Events in JSON format:
```json
{
  "type": "job_updated",
  "data": {
    "job_id": "abc123xyz",
    "filename": "abc123xyz_data.json",
    "stage": "heightmap",
    "location": "outbox",
    "artifact": "/home/...Heightmap/outbox/abc123xyz_data.json",
    "last_log_line": "[12:34:56] Processing heightmap...",
    "updated_at": "2026-01-20T12:34:56Z"
  },
  "timestamp": "2026-01-20T12:34:56Z"
}
```

## Running

**Requirement:** Go 1.21+

### Development Mode

```bash
cd mapgen-web
go mod tidy
go run ./cmd/server
```

Browser: `http://localhost:5003`

### Build & Run

```bash
go build -o bin/server ./cmd/server
./bin/server
```

### Configuration

Edit the constants in `cmd/server/main.go`:
- `httpPort`: Port to bind (default `:5003`)  
- `heightmapAPIURL`: HeightmapAPI endpoint (default `http://localhost:8000`)  
- `logPath`: Path to pipeline logs (default `~/Code/RTSColonyTerrainGenerator/MapGenerator/minicli.log`)

## Filesystem Watching

**Watched Directories:**
- `~/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/{inbox,outbox}`  
- `~/Code/RTSColonyTerrainGenerator/MapGenerator/Tiler/{inbox,outbox}`  
- `~/Code/RTSColonyTerrainGenerator/MapGenerator/WeatherAnalyses/{inbox,outbox}`  
- `~/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter/{inbox,outbox}`  

**Poll Interval:** 1 second (configurable in `main.go`)

**Job ID Extraction:** Filenames like `jobid_data.json` or `jobid.heightmap` → `jobid`

## Log Tracking

The server polls the log file every 2 seconds and extracts lines containing the job ID.  
Most recent matching line is stored and broadcast to clients.

## Frontend

Minimal HTML5 page with:
- Form to start new heightmap jobs  
- Live table of all jobs (stage, location, last log line)  
- Event log of recent updates  
- Auto-reconnects SSE on disconnect  

No frameworks or external dependencies.

## Correctness Notes

- **Thread-safe:** All shared state uses `sync.RWMutex`  
- **No database:** In-memory state only; filesystem is always source of truth  
- **Non-blocking SSE:** Slow clients don't block others (buffered channels)  
- **Error handling:** Graceful degradation; missing dirs don't crash watcher  
- **Simple heuristics:** Job ID extraction is best-effort (adjust as needed)  

## Future Improvements

1. Replace polling with inotify/fsnotify for efficiency  
2. Add job detail page with full log view  
3. Configurable via YAML instead of hardcoded values  
4. Support multiple pipelines (Bandcamp, etc.)  
5. Systemd service integration  
6. Dashboard-to-pipeline control (job retry, manual move)  
