#!/bin/bash
# Quick reference for MapGenerator Control Panel

# Install Go (Arch Linux)
sudo pacman -S go

# Or download directly
wget https://go.dev/dl/go1.25.linux-amd64.tar.gz
tar -xzf go1.25.linux-amd64.tar.gz -C /usr/local

# Verify Go installed
go version

# Build the server
cd ~/Code/RTSColonyTerrainGenerator/mapgen-web
go mod tidy
go build -o bin/server ./cmd/server

# Run the server
./bin/server
# or
go run ./cmd/server

# Test via curl
curl -X POST http://localhost:5003/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512}'

# List jobs
curl http://localhost:5003/api/jobs | jq .

# Stream events (in separate terminal)
curl -N http://localhost:5003/events

# Browser dashboard
# Open: http://localhost:5003

# Key files to understand
# 1. cmd/server/main.go - Entry point, HTTP handlers
# 2. internal/jobs/registry.go - Job state storage
# 3. internal/pipeline/detector.go - HeightmapAPI client
# 4. internal/fswatch/watcher.go - Directory polling
# 5. internal/events/hub.go - Event broadcasting
# 6. web/index.html - Frontend

# Configuration (edit in cmd/server/main.go)
# - httpPort := ":5003"
# - heightmapAPIURL := "http://localhost:8000"
# - logPath := "$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/minicli.log"

# Watched directories (constant polling at 1-second interval)
# - Heightmap/inbox, Heightmap/outbox
# - Tiler/inbox, Tiler/outbox
# - WeatherAnalyses/inbox, WeatherAnalyses/outbox
# - TreePlanter/inbox, TreePlanter/outbox

# Next steps
# 1. Install Go (if not already)
# 2. Build: go build -o bin/server ./cmd/server
# 3. Run: ./bin/server
# 4. Visit: http://localhost:5003
# 5. Trigger job: POST /api/jobs/start with {"width": 512, "height": 512}
# 6. Watch updates stream live to browser via SSE
