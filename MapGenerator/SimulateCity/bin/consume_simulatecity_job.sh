#!/usr/bin/env bash
#
# SimulateCity queue consumer (CivicOverreach v1)
#
# This script processes ONE payload per invocation.
# It is designed to be triggered by a systemd .path unit.
#

set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/SimulateCity"

HEIGHTMAP_OUTBOX="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap/outbox"

LATEST_JOB=$(ls -t "$HEIGHTMAP_OUTBOX"/*.heightmap 2>/dev/null | head -n1 || true)
if [[ -z "$LATEST_JOB" ]]; then
  echo "[SimulateCity] No heightmap jobs in $HEIGHTMAP_OUTBOX"
  exit 0
fi

JOB_ID=$(basename "$LATEST_JOB" .heightmap)

"$STAGE_ROOT/bin/run_civic_overreach.sh" "$JOB_ID"
