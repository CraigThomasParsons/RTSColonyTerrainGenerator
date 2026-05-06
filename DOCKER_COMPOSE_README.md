# RTSColony Terrain Generator - Docker Compose Setup

Complete orchestration for all three services:
- **HeightmapAPI** (PHP) - Enqueue heightmap jobs
- **MapGenerator Web** (Go) - Control plane, track jobs, stream updates
- **Web Dashboard** (Python) - Observe pipelines

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Docker Network (mapgen)                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ heightmap-api│  │ mapgen-web   │  │ web-dash │ │
│  │    (PHP)     │  │     (Go)     │  │ (Python) │ │
│  │   :8080      │  │   :5003      │  │  :5001   │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│         ▲                ▲                 ▲       │
│         │  HTTP calls    │ reads config    │       │
│         └────────────────┴─────────────────┘       │
│                                                     │
└─────────────────────────────────────────────────────┘
         ▲                    ▲                ▲
         │                    │                │
    localhost:8099       localhost:5003   localhost:5001
```

## Quick Start

### Start All Services
```bash
cd ~/Code/RTSColonyTerrainGenerator
docker-compose up -d

# Check status
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mapgen-web
docker-compose logs -f heightmap-api
docker-compose logs -f web-dashboard
```

### Stop All Services
```bash
docker-compose down
```

## Services

### heightmap-api (Port 8099)
- **Purpose:** Enqueue heightmap jobs
- **Endpoint:** `POST http://heightmap-api:8080/enqueue`
- **Request:** `{"width": 512, "height": 512}`
- **Response:** `{"ok": true, "job_id": "...", "job_file": "..."}`

### mapgen-web (Port 5003)
- **Purpose:** Control plane for MapGenerator
- **Endpoints:**
  - `GET /` - HTML dashboard
  - `POST /api/jobs/start` - Start job
  - `GET /api/jobs` - List jobs
  - `GET /events` - SSE stream
- **Environment Variables:**
  - `HEIGHTMAP_API_URL=http://heightmap-api:8080` (default)
  - `PIPELINE_ROOT=/data/MapGenerator` (default)
  - `LOG_PATH=/data/logs/minicli.log` (default)

### web-dashboard (Port 5001)
- **Purpose:** Observe pipeline stages
- **Endpoint:** `GET /`
- **Features:** Multi-pipeline support, queue visualization, systemd integration

## Network

All services are on the `mapgen` network, allowing them to communicate via hostname:

```
mapgen-web → http://heightmap-api:8080
web-dashboard → reads from /pipelines/MapGenerator
```

## Volumes

| Service | Mount | Purpose |
|---------|-------|---------|
| heightmap-api | `./MapGenerator/Heightmap:/app/Heightmap` | Job input/output |
| mapgen-web | `./MapGenerator:/data/MapGenerator` | Watch pipeline stages |
| mapgen-web | `./logs:/data/logs` | Access logs |
| web-dashboard | `./MapGenerator:/pipelines/MapGenerator` | Monitor pipelines |

## Configuration

### Environment Variables (in docker-compose.yml)

**mapgen-web:**
```yaml
environment:
  - HEIGHTMAP_API_URL=http://heightmap-api:8080
  - LOG_PATH=/data/minicli.log
  - PIPELINE_ROOT=/data/MapGenerator
```

### Modify Configuration

Edit `docker-compose.yml` and restart:
```bash
docker-compose down
# Edit docker-compose.yml
docker-compose up -d
```

## Testing

### Start Services
```bash
docker-compose up -d
```

### Test HeightmapAPI
```bash
curl -X POST http://localhost:8099/enqueue \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512}'
```

### Test MapGenerator Web
```bash
# Start a job
curl -X POST http://localhost:5003/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512}'

# List jobs
curl http://localhost:5003/api/jobs | jq .

# Open dashboard
open http://localhost:5003
```

### Test Web Dashboard
```bash
open http://localhost:5001
```

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs mapgen-web
```

### Rebuild Images
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Clear Volumes
```bash
docker-compose down -v
docker-compose up -d
```

### Check Network
```bash
docker network ls
docker network inspect rtscolonyterraingenerator_mapgen
```

### Exec into Container
```bash
docker-compose exec mapgen-web sh
docker-compose exec heightmap-api bash
docker-compose exec web-dashboard bash
```

## Performance Notes

- **Network:** Bridge network with minimal overhead
- **Volumes:** Direct bind mounts for MapGenerator directory
- **Restart Policy:** `unless-stopped` (auto-restart on failure)
- **Dependencies:** `mapgen-web` waits for `heightmap-api` to start

## Development vs Production

### Development (Current)
- Binds to `127.0.0.1` (localhost only)
- All services on same Docker network
- Direct volume mounts to source directories
- Logs visible via `docker-compose logs`

### Production Changes Needed
- Bind to `0.0.0.0` for external access
- Add authentication/API keys
- Use Docker secrets for config
- Mount volumes as read-only where applicable
- Add health checks
- Add resource limits

## File Structure

```
RTSColonyTerrainGenerator/
├── docker-compose.yml          ← Master orchestration (NEW)
├── mapgen-web/
│   ├── Dockerfile              ← Go service image (NEW)
│   ├── cmd/server/main.go      ← Updated for env vars
│   └── internal/fswatch/       ← Updated for env vars
├── HeightmapApi/
│   ├── Dockerfile              ← Existing
│   └── docker-compose.yml      ← Can be deprecated
└── Web/
    ├── Dockerfile              ← Python service image (NEW)
    └── server/
```

## Migration from Individual docker-compose Files

Previously:
```bash
cd HeightmapApi && docker-compose up -d
cd Web && ./install.sh
```

Now (all in one):
```bash
docker-compose up -d
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Remove everything
docker system prune -a
```

## Next Steps

1. Ensure MapGenerator, Heightmap, and logs directories exist
2. Run `docker-compose up -d` from project root
3. Visit dashboards:
   - http://localhost:5003 (MapGenerator Control)
   - http://localhost:5001 (Pipeline Observer)
4. Start a job via curl or browser UI

---

**Status:** ✅ Complete orchestration with inter-service communication
