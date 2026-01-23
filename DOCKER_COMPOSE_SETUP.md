# Docker Compose Setup - Complete

## Summary

Created a unified `docker-compose.yml` at the project root that orchestrates all three services:

```
/RTSColonyTerrainGenerator/docker-compose.yml
├── heightmap-api (PHP, port 8099)
├── mapgen-web (Go, port 5003)  
└── web-dashboard (Python, port 5001)
```

All services are on the same Docker network (`mapgen`) and can communicate via service names.

## Files Created/Modified

### New Dockerfiles
- `mapgen-web/Dockerfile` - Go build + runtime image
- `Web/Dockerfile` - Python Flask image

### Main Orchestration
- `docker-compose.yml` - Master compose file at project root

### Documentation
- `DOCKER_COMPOSE_README.md` - Complete setup & usage guide

### Code Updates (for Docker compatibility)
- `mapgen-web/cmd/server/main.go` - Environment variables for config
- `mapgen-web/internal/fswatch/watcher.go` - Relative paths + env var support

## Architecture

```
┌─────────────────────────────────────────────────────┐
│        Docker Network: mapgen (bridge)              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  heightmap-api        mapgen-web       web-dashboard│
│   (PHP)                (Go)              (Python)   │
│  :8080 internal     :5003 internal       :5001      │
│   ↑ localhost       ↓ hostname call                 │
│   ↑                 http://                         │
│   └──────────────── heightmap-api:8080             │
│                                                     │
│  Shared Volume: ./MapGenerator/*                    │
│                                                     │
└─────────────────────────────────────────────────────┘
         ↓              ↓               ↓
   localhost:8099  localhost:5003  localhost:5001
```

## Quick Start

```bash
cd ~/Code/RTSColonyTerrainGenerator

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Service Communication

- **mapgen-web calls heightmap-api** via `http://heightmap-api:8080`
- **Inter-service communication** uses Docker DNS (service names)
- **External access** uses localhost ports (8099, 5003, 5001)

## Environment Variables

Services automatically read environment variables from docker-compose.yml:

**mapgen-web:**
```
HEIGHTMAP_API_URL=http://heightmap-api:8080  (service name, not localhost)
LOG_PATH=/data/minicli.log
PIPELINE_ROOT=/data/MapGenerator
```

## Volume Mounts

| Service | Mount | Purpose |
|---------|-------|---------|
| heightmap-api | `./MapGenerator/Heightmap:/app/Heightmap` | Job input/output |
| mapgen-web | `./MapGenerator:/data/MapGenerator` | Watch stages |
| web-dashboard | `./MapGenerator:/pipelines/MapGenerator` | Monitor stages |

## Testing Commands

```bash
# Test HeightmapAPI
curl -X POST http://localhost:8099/enqueue \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512}'

# Test MapGen Web
curl http://localhost:5003/api/jobs | jq .

# Open dashboards
open http://localhost:5003  # MapGen control plane
open http://localhost:5001  # Pipeline observer
```

## Network Details

Created network: `rtscolonyterraingenerator_mapgen`

```bash
# View network
docker network inspect rtscolonyterraingenerator_mapgen

# Services see each other as:
heightmap-api:8080
mapgen-web:5003
web-dashboard:5001
```

## Logs & Debugging

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mapgen-web
docker-compose logs -f heightmap-api
docker-compose logs -f web-dashboard

# Exec into container
docker-compose exec mapgen-web sh
docker-compose exec heightmap-api bash
```

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean everything
docker system prune -a
```

## Advantages Over Individual Setups

✅ **Single command to start all services** (`docker-compose up -d`)
✅ **Automatic networking** (mapgen-web finds heightmap-api via DNS)
✅ **Service dependencies managed** (mapgen-web depends on heightmap-api)
✅ **Consistent volume mounts** across all services
✅ **Unified logging** (`docker-compose logs`)
✅ **Easy teardown** (`docker-compose down`)

## Configuration Changes

To modify service config, edit `docker-compose.yml`:

```yaml
mapgen-web:
  environment:
    - HEIGHTMAP_API_URL=http://heightmap-api:8080  # Change if needed
    - LOG_PATH=/data/minicli.log
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## What's Next

1. ✅ Created unified docker-compose.yml
2. ✅ Created Dockerfiles for mapgen-web and Web
3. ✅ Updated mapgen-web for environment variables
4. ✅ Tested service startup and basic endpoints
5. ⏭️ (Optional) Add health checks to docker-compose.yml
6. ⏭️ (Optional) Create production-ready docker-compose.prod.yml

## Current Status

```
✅ docker-compose.yml created & tested
✅ All three services building successfully
✅ All services running and responding
✅ Inter-service networking operational
✅ Documentation complete
```

---

**See [DOCKER_COMPOSE_README.md](DOCKER_COMPOSE_README.md) for complete documentation.**
