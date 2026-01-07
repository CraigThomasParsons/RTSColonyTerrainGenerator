#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Tiler"
INBOX="$ROOT/inbox"
ARCHIVE="$ROOT/archive"
FAILED="$ROOT/failed"

mkdir -p "$ARCHIVE" "$FAILED"

job=$(ls "$INBOX"/*.heightmap 2>/dev/null | head -n 1 || true)

if [[ -z "$job" ]]; then
  echo "[tiler] No jobs in inbox"
  exit 0
fi

job_id=$(basename "$job" .heightmap)

echo "[tiler] Processing job $job_id"

if "$ROOT/bin/tiler.sh" "$job"; then
  mv "$job" "$ARCHIVE/$job_id.heightmap"
  echo "[tiler] Job $job_id complete"
else
  mv "$job" "$FAILED/$job_id.heightmap"
  echo "[tiler] Job $job_id failed"
fi
