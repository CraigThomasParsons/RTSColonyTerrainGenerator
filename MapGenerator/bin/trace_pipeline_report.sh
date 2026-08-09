#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
JOB_ID="${1:-}"

find_latest_job() {
  local candidate
  for dir in \
    "$REPO_ROOT/MapGenerator/Playable/outbox" \
    "$REPO_ROOT/MapGenerator/WorldFeatures/outbox" \
    "$REPO_ROOT/MapGenerator/TreePlanter/outbox"
  do
    candidate=$(ls -t "$dir"/*.worldpayload 2>/dev/null | head -n1 || true)
    if [[ -n "$candidate" ]]; then
      basename "$candidate" .worldpayload
      return
    fi
  done

  local stargus_dir="$REPO_ROOT/MapGenerator/StargusExport/outbox"
  candidate=$(ls -t "$stargus_dir"/*.scm 2>/dev/null | head -n1 || true)
  if [[ -n "$candidate" ]]; then
    basename "$candidate" .scm
    return
  fi
}

if [[ -z "$JOB_ID" ]]; then
  JOB_ID="$(find_latest_job || true)"
fi

if [[ -z "$JOB_ID" ]]; then
  echo "[trace] No job id found."
  exit 1
fi

echo "[trace] Job ID: $JOB_ID"
echo

print_artifact() {
  local label="$1"
  local path="$2"
  if [[ -f "$path" ]]; then
    local size
    local mtime
    size=$(stat -c '%s' "$path" 2>/dev/null || echo "?")
    mtime=$(stat -c '%y' "$path" 2>/dev/null || echo "?")
    printf "%-14s OK  %s  (%s bytes)\n" "$label" "$path" "$size"
    printf "                mtime: %s\n" "$mtime"
  else
    printf "%-14s MISSING  %s\n" "$label" "$path"
  fi
}

print_artifact "heightmap" "$REPO_ROOT/MapGenerator/Heightmap/outbox/$JOB_ID.heightmap"
print_artifact "maptiles" "$REPO_ROOT/MapGenerator/Tiler/outbox/$JOB_ID.maptiles"
print_artifact "weather" "$REPO_ROOT/MapGenerator/WeatherAnalyses/outbox/$JOB_ID.weather"
print_artifact "treeplanter" "$REPO_ROOT/MapGenerator/TreePlanter/outbox/$JOB_ID.worldpayload"
print_artifact "worldfeatures" "$REPO_ROOT/MapGenerator/WorldFeatures/outbox/$JOB_ID.worldpayload"
print_artifact "playable" "$REPO_ROOT/MapGenerator/Playable/outbox/$JOB_ID.worldpayload"
print_artifact "playable.json" "$REPO_ROOT/MapGenerator/Playable/outbox/$JOB_ID.playable.json"
print_artifact "stargus.chk" "$REPO_ROOT/MapGenerator/StargusExport/outbox/$JOB_ID.chk"
print_artifact "stargus.scm" "$REPO_ROOT/MapGenerator/StargusExport/outbox/$JOB_ID.scm"

echo
echo "[trace] Stargus maps folder:"
echo "  $HOME/.stratagus/sc/maps/MapGeneratorOutput/$JOB_ID.scm"
