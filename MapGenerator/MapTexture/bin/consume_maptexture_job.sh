#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${MAPGEN_REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
STAGE_ROOT="$REPO_ROOT/MapGenerator/MapTexture"
PLAYABLE_OUT="${MAPTEXTURE_PLAYABLE_OUT:-$REPO_ROOT/MapGenerator/Playable/outbox}"
HEIGHTMAP_OUT="${MAPTEXTURE_HEIGHTMAP_OUT:-$REPO_ROOT/MapGenerator/Heightmap/outbox}"
HEIGHTMAP_PNG_OUT="${MAPTEXTURE_HEIGHTMAP_PNG_OUT:-$REPO_ROOT/MapGenerator/SimulateCity/inbox}"
OUTPUT_ROOT="${MAPTEXTURE_OUTPUT_ROOT:-$STAGE_ROOT/outbox}"

job_id="${1:-}"
if [[ -z "$job_id" ]]; then
  playable_file="$(find "$PLAYABLE_OUT" -maxdepth 1 -name '*.playable.json' -printf '%T@ %f\n' | sort -nr | head -1 | cut -d' ' -f2-)"
  [[ -n "$playable_file" ]] || { echo "No Playable artifact available" >&2; exit 2; }
  job_id="${playable_file%.playable.json}"
fi

height_png="$(find "$HEIGHTMAP_PNG_OUT" -maxdepth 2 -type f -name "*${job_id}*.png" | head -1)"
[[ -n "$height_png" ]] || { echo "Heightmap PNG not found for $job_id" >&2; exit 2; }

python3 "$STAGE_ROOT/bin/maptexture.py" run \
  --heightmap "$HEIGHTMAP_OUT/$job_id.heightmap" \
  --heightmap-png "$height_png" \
  --worldpayload "$PLAYABLE_OUT/$job_id.worldpayload" \
  --playable "$PLAYABLE_OUT/$job_id.playable.json" \
  --output "$OUTPUT_ROOT/$job_id"
