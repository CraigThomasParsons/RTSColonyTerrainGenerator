#!/usr/bin/env bash
#
# CivicOverreach runner (Phase 1)
#
# Responsibilities:
# - Accept a job_id
# - Locate Heightmap/outbox/<job_id>/
# - Copy required heightmap artifacts locally
# - Execute civic_overreach.py with explicit paths
# - Write <job_id>.civic_overreach.worldpayload to outbox
# - Never mutate input artifacts
# - Exit cleanly on partial failure
#

set -euo pipefail

JOB_ID="${1:-}"
if [[ -z "$JOB_ID" ]]; then
  echo "[CivicOverreach] Missing job_id" >&2
  exit 1
fi

REPO_ROOT="$HOME/Code/RTSColonyTerrainGenerator"
HEIGHTMAP_OUTBOX="$REPO_ROOT/MapGenerator/Heightmap/outbox"
STAGE_ROOT="$REPO_ROOT/MapGenerator/CivicOverreach"

SOURCE_DIR="$HEIGHTMAP_OUTBOX/$JOB_ID"
HEIGHTMAP_BIN="$HEIGHTMAP_OUTBOX/$JOB_ID.heightmap"

WORK_DIR="$STAGE_ROOT/inbox/$JOB_ID"
OUTBOX_DIR="$STAGE_ROOT/outbox"
LOG_DIR="$STAGE_ROOT/logs"
LOG_FILE="$LOG_DIR/$JOB_ID.civic_overreach.log"
OUTPUT_FILE="$OUTBOX_DIR/$JOB_ID.civic_overreach.worldpayload"

mkdir -p "$WORK_DIR" "$OUTBOX_DIR" "$LOG_DIR"

if [[ -f "$OUTPUT_FILE" ]]; then
  echo "[CivicOverreach] Output exists, skipping: $OUTPUT_FILE" | tee -a "$LOG_FILE"
  exit 0
fi

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -d "$SOURCE_DIR" ]]; then
  cp -f "$SOURCE_DIR"/heightmap_*.png "$WORK_DIR/" 2>/dev/null || true
  cp -f "$SOURCE_DIR"/heightmap.meta.json "$WORK_DIR/" 2>/dev/null || true
else
  if [[ ! -f "$HEIGHTMAP_BIN" ]]; then
    echo "[CivicOverreach] Missing heightmap artifacts for $JOB_ID" | tee -a "$LOG_FILE"
    exit 0
  fi

  cp -f "$HEIGHTMAP_BIN" "$WORK_DIR/$JOB_ID.heightmap"

  "$PYTHON_BIN" \
    "$REPO_ROOT/MapGenerator/Heightmap/bin/export_heightmap_png.py" \
    --input "$HEIGHTMAP_BIN" \
    --output-dir "$WORK_DIR" \
    --job-id "$JOB_ID" \
    2>&1 | tee -a "$LOG_FILE"
fi

if [[ ! -f "$WORK_DIR/heightmap.meta.json" ]]; then
  echo "[CivicOverreach] Missing heightmap.meta.json" | tee -a "$LOG_FILE"
  exit 0
fi

PNG_COUNT=$(ls "$WORK_DIR"/heightmap_*.png 2>/dev/null | wc -l | tr -d ' ')
if [[ "$PNG_COUNT" == "0" ]]; then
  echo "[CivicOverreach] Missing heightmap PNG" | tee -a "$LOG_FILE"
  exit 0
fi

"$PYTHON_BIN" \
  "$STAGE_ROOT/bin/civic_overreach.py" \
  --input-dir "$WORK_DIR" \
  --output-dir "$OUTBOX_DIR" \
  --log-dir "$LOG_DIR" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$OUTPUT_FILE" ]]; then
  echo "[CivicOverreach] Output missing after run" | tee -a "$LOG_FILE"
  exit 0
fi

"$PYTHON_BIN" - <<PY 2>/dev/null | tee -a "$LOG_FILE"
import json
from pathlib import Path

payload = json.loads(Path("""$OUTPUT_FILE""").read_text(encoding="utf-8"))
concrete = payload.get("concrete", {})
heuristics = payload.get("heuristics", {})

bridges = concrete.get("bridges", [])
roads = concrete.get("roads", [])
buildings = concrete.get("buildings", [])

islands = [z for z in heuristics.get("overreach_zones", []) if z.get("type") == "island"]

disasters = heuristics.get("disaster_events", [])
maint = heuristics.get("maintenance_failures", [])

print("[CivicOverreach] islands_detected=", len(islands))
print("[CivicOverreach] bridges_attempted=", len(bridges))
print("[CivicOverreach] disasters_applied=", len(disasters) + len(maint))
print("[CivicOverreach] ruins_emitted=", len(bridges) + len(roads) + len(buildings))
PY
